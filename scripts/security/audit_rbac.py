"""Audit deployed RBAC against `infrastructure/security/capabilities.yaml`.

Detects three kinds of drift:

  MISSING   capabilities.yaml says X should exist; the cluster has no X
  EXTRA     cluster has Y; capabilities.yaml doesn't define it
  MISMATCH  X exists on both sides but contents differ (verbs, subjects,
            resourceNames, etc.) — usually means somebody hand-edited

Exit codes:
  0  match — deployed RBAC equals desired
  1  drift detected (any finding with severity error or warning)
  2  invocation error (kubectl failed, capabilities.yaml missing, etc.)

Usage:

    # Live cluster
    python scripts/security/audit_rbac.py

    # Offline / CI: feed the kubectl JSON in
    kubectl get sa,role,rolebinding -n synthetic-enterprise -o json \\
        > /tmp/state.json
    python scripts/security/audit_rbac.py --from-json /tmp/state.json

The script intentionally reuses `generate_policies.build_rbac` so the
"expected" side of the comparison is identical bytes to what the
generator would emit. Drift = generator-output != cluster-state.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from scripts.security import generate_policies


# Generic SAs/Roles/Bindings that exist in namespace.yaml (not per-agent).
# We don't flag these as "EXTRA" even though capabilities.yaml doesn't list them.
NAMESPACE_LEVEL_NAMES = {
    "serviceaccounts": {"default", "agent-sa"},
    "roles": {"agent-role"},
    "rolebindings": {"agent-rolebinding"},
}


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    kind: str           # "MISSING" | "EXTRA" | "MISMATCH"
    resource: str       # "ServiceAccount" | "Role" | "RoleBinding"
    name: str
    severity: Severity
    detail: str
    remediation: str

    def format(self) -> str:
        return (
            f"[{self.severity.value.upper():7}] {self.kind:<8} "
            f"{self.resource}/{self.name}\n"
            f"          {self.detail}\n"
            f"          fix: {self.remediation}"
        )


def expected_state(capabilities_path: Path) -> dict[str, dict[str, dict[str, Any]]]:
    """Build the desired state map: {kind: {name: doc}}."""
    spec = generate_policies.load_capabilities(capabilities_path)
    out: dict[str, dict[str, dict[str, Any]]] = {
        "ServiceAccount": {},
        "Role": {},
        "RoleBinding": {},
    }
    for agent_name in sorted(spec["agents"]):
        agent = spec["agents"][agent_name]
        for doc in generate_policies.build_rbac(agent_name, agent, spec):
            out[doc["kind"]][doc["metadata"]["name"]] = doc
    return out


def actual_state(kubectl_json: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    """Bucket `kubectl get sa,role,rolebinding -o json` output by kind+name."""
    out: dict[str, dict[str, dict[str, Any]]] = {
        "ServiceAccount": {},
        "Role": {},
        "RoleBinding": {},
    }
    for item in kubectl_json.get("items", []):
        kind = item.get("kind")
        name = item.get("metadata", {}).get("name")
        if kind in out and name:
            out[kind][name] = item
    return out


def _normalize_rule(rule: dict[str, Any]) -> tuple:
    """A hashable, comparison-stable form of a Role rule."""
    return (
        tuple(sorted(rule.get("apiGroups", []))),
        tuple(sorted(rule.get("resources", []))),
        tuple(sorted(rule.get("resourceNames", []))),
        tuple(sorted(rule.get("verbs", []))),
    )


def diff_role(expected: dict, actual: dict) -> list[str]:
    """Return human-readable diff lines between two Role specs.

    Empty list = identical.
    """
    diffs: list[str] = []
    exp_rules = {_normalize_rule(r) for r in expected.get("rules", [])}
    act_rules = {_normalize_rule(r) for r in actual.get("rules", [])}
    only_expected = exp_rules - act_rules
    only_actual = act_rules - exp_rules
    for rule in sorted(only_expected):
        diffs.append(f"missing rule: {dict(zip(['apiGroups','resources','resourceNames','verbs'], rule))}")
    for rule in sorted(only_actual):
        diffs.append(f"unexpected rule: {dict(zip(['apiGroups','resources','resourceNames','verbs'], rule))}")
    return diffs


def diff_rolebinding(expected: dict, actual: dict) -> list[str]:
    diffs: list[str] = []
    exp_subjects = {(s.get("kind"), s.get("name"), s.get("namespace")) for s in expected.get("subjects", [])}
    act_subjects = {(s.get("kind"), s.get("name"), s.get("namespace")) for s in actual.get("subjects", [])}
    if exp_subjects != act_subjects:
        diffs.append(f"subjects differ: expected={sorted(exp_subjects)} actual={sorted(act_subjects)}")
    exp_ref = expected.get("roleRef", {})
    act_ref = actual.get("roleRef", {})
    if (exp_ref.get("kind"), exp_ref.get("name")) != (act_ref.get("kind"), act_ref.get("name")):
        diffs.append(f"roleRef differs: expected={exp_ref} actual={act_ref}")
    return diffs


def audit(
    expected: dict[str, dict[str, dict[str, Any]]],
    actual: dict[str, dict[str, dict[str, Any]]],
) -> list[Finding]:
    """Compare expected vs actual; return findings sorted by severity."""
    findings: list[Finding] = []

    for kind in ("ServiceAccount", "Role", "RoleBinding"):
        exp_names = set(expected[kind])
        act_names = set(actual[kind])

        # MISSING: expected but absent.
        for name in sorted(exp_names - act_names):
            findings.append(Finding(
                kind="MISSING",
                resource=kind,
                name=name,
                severity=Severity.ERROR,
                detail=f"capabilities.yaml requires {kind}/{name} but the cluster has no such object",
                remediation=(
                    f"re-run scripts/security/generate_policies.py then "
                    f"kubectl apply -f infrastructure/k3s/rbac-per-agent.yaml"
                ),
            ))

        # EXTRA: present but not declared (warning — could be intentional).
        kind_lower = kind.lower() + "s"
        builtin = NAMESPACE_LEVEL_NAMES.get(kind_lower, set())
        for name in sorted(act_names - exp_names):
            if name in builtin:
                continue   # namespace.yaml's generic SA/Role/Binding
            findings.append(Finding(
                kind="EXTRA",
                resource=kind,
                name=name,
                severity=Severity.WARNING,
                detail=f"cluster has {kind}/{name}; not declared in capabilities.yaml",
                remediation=(
                    f"either delete (`kubectl delete {kind_lower[:-1]} {name} -n synthetic-enterprise`) "
                    "or add it to infrastructure/security/capabilities.yaml"
                ),
            ))

        # MISMATCH: present in both, but contents differ.
        for name in sorted(exp_names & act_names):
            if kind == "ServiceAccount":
                continue   # SA has no spec; existence is sufficient
            exp = expected[kind][name]
            act = actual[kind][name]
            if kind == "Role":
                diffs = diff_role(exp, act)
            elif kind == "RoleBinding":
                diffs = diff_rolebinding(exp, act)
            else:
                diffs = []
            if diffs:
                findings.append(Finding(
                    kind="MISMATCH",
                    resource=kind,
                    name=name,
                    severity=Severity.ERROR,
                    detail="; ".join(diffs),
                    remediation=(
                        f"re-apply infrastructure/k3s/rbac-per-agent.yaml to overwrite "
                        f"manual edits; if intentional, update capabilities.yaml + regenerate"
                    ),
                ))

    severity_order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}
    findings.sort(key=lambda f: (severity_order[f.severity], f.resource, f.name))
    return findings


def fetch_kubectl_json(namespace: str) -> dict[str, Any]:
    """Run kubectl and return the parsed JSON. Raises on non-zero exit."""
    proc = subprocess.run(
        ["kubectl", "get", "sa,role,rolebinding", "-n", namespace, "-o", "json",
         "--request-timeout=10s"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"kubectl failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capabilities", type=Path,
                        default=Path("infrastructure/security/capabilities.yaml"))
    parser.add_argument("--from-json", type=Path,
                        help="Read cluster state from a kubectl JSON file instead of running kubectl")
    parser.add_argument("--namespace", default=None,
                        help="Defaults to capabilities.yaml's namespace")
    parser.add_argument("--quiet", action="store_true",
                        help="Only print findings + summary; no INFO chatter")
    args = parser.parse_args(argv)

    if not args.capabilities.is_file():
        print(f"ERROR: {args.capabilities} not found", file=sys.stderr)
        return 2

    spec = generate_policies.load_capabilities(args.capabilities)
    namespace = args.namespace or spec["namespace"]
    expected = expected_state(args.capabilities)

    try:
        if args.from_json:
            kubectl_json = json.loads(args.from_json.read_text(encoding="utf-8"))
        else:
            kubectl_json = fetch_kubectl_json(namespace)
    except Exception as exc:
        print(f"ERROR: could not load cluster state: {exc}", file=sys.stderr)
        return 2

    actual = actual_state(kubectl_json)
    findings = audit(expected, actual)

    if not args.quiet:
        print(f"RBAC audit: namespace={namespace} "
              f"expected_sas={len(expected['ServiceAccount'])} "
              f"actual_sas={len(actual['ServiceAccount'])}")

    if not findings:
        print("OK: deployed RBAC matches capabilities.yaml")
        return 0

    for f in findings:
        print(f.format())
    n_err = sum(1 for f in findings if f.severity == Severity.ERROR)
    n_warn = sum(1 for f in findings if f.severity == Severity.WARNING)
    print(f"\nDRIFT: {len(findings)} finding(s) — {n_err} error(s), {n_warn} warning(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
