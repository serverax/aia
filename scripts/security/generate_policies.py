"""Generate per-agent NetworkPolicy + RBAC from capabilities.yaml.

Run from repo root:

    python scripts/security/generate_policies.py

Or against a custom input path:

    python scripts/security/generate_policies.py \\
        --in infrastructure/security/capabilities.yaml \\
        --network-out infrastructure/k3s/network-policies-per-agent.yaml \\
        --rbac-out infrastructure/k3s/rbac-per-agent.yaml

Outputs are deterministic (sorted keys, stable list order) so re-running
without source changes produces a byte-identical file. CI gate:
`git diff --exit-code infrastructure/k3s/network-policies-per-agent.yaml`
after running the generator catches drift between capabilities.yaml and
the committed manifests.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

# Private CIDR ranges excluded from external egress rules so "allow
# external" doesn't accidentally grant cluster-internal access (which is
# governed by the in-cluster egress_allow list instead).
RFC1918_CIDRS = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]


def load_capabilities(path: Path) -> dict[str, Any]:
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for required in ("version", "namespace", "services", "agents"):
        if required not in spec:
            raise ValueError(f"capabilities.yaml missing required field {required!r}")
    if spec["version"] != 1:
        raise ValueError(f"unsupported capabilities.yaml version {spec['version']}")
    return spec


def build_network_policy(agent_name: str, agent: dict, spec: dict) -> dict:
    """One NetworkPolicy per agent. Default-deny applies cluster-wide; this
    layers per-agent egress allowances on top."""
    namespace = spec["namespace"]
    services = spec["services"]
    external = spec.get("external", {})
    network = agent.get("network", {})

    egress: list[dict] = []

    for service_name in network.get("egress_allow", []):
        if service_name not in services:
            raise ValueError(f"agent {agent_name!r} references unknown service {service_name!r}")
        svc = services[service_name]
        egress.append(
            {
                "to": [{"podSelector": {"matchLabels": dict(svc["selector"])}}],
                "ports": [dict(p) for p in svc["ports"]],
            }
        )

    for external_name in network.get("external_allow", []):
        if external_name not in external:
            raise ValueError(f"agent {agent_name!r} references unknown external {external_name!r}")
        ext = external[external_name]
        egress.append(
            {
                "to": [{"ipBlock": {"cidr": "0.0.0.0/0", "except": list(RFC1918_CIDRS)}}],
                "ports": [dict(p) for p in ext["ports"]],
            }
        )

    # DNS to kube-system is always allowed — no agent works without it.
    # `kubernetes.io/metadata.name` is auto-applied by the apiserver since
    # k8s 1.22; the older convention `name: <namespace>` requires a manual
    # `kubectl label`, which silently broke DNS egress on fresh clusters.
    egress.append(
        {
            "to": [
                {
                    "namespaceSelector": {
                        "matchLabels": {"kubernetes.io/metadata.name": "kube-system"}
                    }
                }
            ],
            "ports": [
                {"port": 53, "protocol": "UDP"},
                {"port": 53, "protocol": "TCP"},
            ],
        }
    )

    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": {
            "name": f"{agent_name}-agent-egress",
            "namespace": namespace,
        },
        "spec": {
            "podSelector": {"matchLabels": dict(agent["pod_selector"])},
            "policyTypes": ["Egress"],
            "egress": egress,
        },
    }


def build_rbac(agent_name: str, agent: dict, spec: dict) -> list[dict]:
    """ServiceAccount + Role + RoleBinding triple per agent."""
    namespace = spec["namespace"]
    rbac = agent.get("rbac", {})
    sa_name = f"{agent_name}-agent-sa"
    role_name = f"{agent_name}-agent-role"
    binding_name = f"{agent_name}-agent-rolebinding"

    docs: list[dict] = [
        {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {"name": sa_name, "namespace": namespace},
        }
    ]

    rules: list[dict] = []
    secrets = sorted(rbac.get("secrets", []))
    if secrets:
        rules.append(
            {
                "apiGroups": [""],
                "resources": ["secrets"],
                "resourceNames": secrets,
                "verbs": ["get", "list"],
            }
        )
    configmaps = sorted(rbac.get("configmaps", []))
    if configmaps:
        rules.append(
            {
                "apiGroups": [""],
                "resources": ["configmaps"],
                "resourceNames": configmaps,
                "verbs": ["get", "list"],
            }
        )

    docs.append(
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "Role",
            "metadata": {"name": role_name, "namespace": namespace},
            "rules": rules,
        }
    )

    docs.append(
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "RoleBinding",
            "metadata": {"name": binding_name, "namespace": namespace},
            "subjects": [{"kind": "ServiceAccount", "name": sa_name, "namespace": namespace}],
            "roleRef": {
                "apiGroup": "rbac.authorization.k8s.io",
                "kind": "Role",
                "name": role_name,
            },
        }
    )

    return docs


def emit_yaml(docs: list[dict], path: Path, *, header: str) -> None:
    """Write multi-doc YAML with a fixed header comment."""
    path.parent.mkdir(parents=True, exist_ok=True)
    buf: list[str] = [header.rstrip(), ""]
    for doc in docs:
        buf.append("---")
        buf.append(yaml.safe_dump(doc, sort_keys=False, default_flow_style=False).rstrip())
    path.write_text("\n".join(buf) + "\n", encoding="utf-8")


def generate(
    capabilities_path: Path,
    network_out: Path,
    rbac_out: Path,
) -> tuple[int, int]:
    """Returns (n_network_docs, n_rbac_docs)."""
    spec = load_capabilities(capabilities_path)
    agents = spec["agents"]

    network_docs: list[dict] = []
    rbac_docs: list[dict] = []

    for agent_name in sorted(agents):
        agent = agents[agent_name]
        network_docs.append(build_network_policy(agent_name, agent, spec))
        rbac_docs.extend(build_rbac(agent_name, agent, spec))

    network_header = (
        "# AUTOGENERATED by scripts/security/generate_policies.py\n"
        "# Source: infrastructure/security/capabilities.yaml\n"
        "# Do not edit directly — modify capabilities.yaml and re-run the generator."
    )
    rbac_header = (
        "# AUTOGENERATED by scripts/security/generate_policies.py\n"
        "# Source: infrastructure/security/capabilities.yaml\n"
        "# Do not edit directly — modify capabilities.yaml and re-run the generator."
    )

    emit_yaml(network_docs, network_out, header=network_header)
    emit_yaml(rbac_docs, rbac_out, header=rbac_header)

    return len(network_docs), len(rbac_docs)


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in", dest="capabilities", default="infrastructure/security/capabilities.yaml"
    )
    parser.add_argument(
        "--network-out", default="infrastructure/k3s/network-policies-per-agent.yaml"
    )
    parser.add_argument("--rbac-out", default="infrastructure/k3s/rbac-per-agent.yaml")
    args = parser.parse_args()

    n_net, n_rbac = generate(
        Path(args.capabilities),
        Path(args.network_out),
        Path(args.rbac_out),
    )
    print(f"wrote {args.network_out} ({n_net} NetworkPolicies)")
    print(f"wrote {args.rbac_out} ({n_rbac} RBAC docs)")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
