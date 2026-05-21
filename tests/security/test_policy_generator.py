"""Unit tests for `scripts/security/generate_policies.py`.

Lives under tests/security/ alongside the other Sprint 6 security tests
but is marked `unit` (not `security`) — it exercises pure-Python code
with no cluster dependency.

Coverage focus: the generator's three pure functions (`load_capabilities`,
`build_network_policy`, `build_rbac`) + the deterministic emit path, plus
a regression test for the Day 8 DNS selector bug.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# Generator is a real package (scripts/security/__init__.py exists) so we
# can import it normally — that's what lets coverage track it.
from scripts.security import generate_policies as _gen_module

pytestmark = [pytest.mark.unit]


_GENERATOR_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts" / "security" / "generate_policies.py"
)


@pytest.fixture(scope="module")
def gen():
    return _gen_module


# --- minimum-viable capability spec used by most tests --------------------

MINIMAL_SPEC = {
    "version": 1,
    "namespace": "test-ns",
    "services": {
        "redis": {
            "selector": {"app": "redis"},
            "ports": [{"port": 6379, "protocol": "TCP"}],
        },
        "postgres": {
            "selector": {"app": "postgres"},
            "ports": [{"port": 5432, "protocol": "TCP"}],
        },
    },
    "external": {
        "anthropic": {
            "ports": [{"port": 443, "protocol": "TCP"}],
            "description": "Claude API",
        },
    },
    "agents": {
        "echo": {
            "pod_selector": {"app": "echo-agent"},
            "network": {"egress_allow": ["redis", "postgres"]},
            "rbac": {
                "secrets": ["postgres-credentials"],
                "configmaps": ["echo-agent-config"],
            },
        },
        "orchestrator": {
            "pod_selector": {"app": "orchestrator-agent"},
            "network": {
                "egress_allow": ["redis"],
                "external_allow": ["anthropic"],
            },
            "rbac": {
                "secrets": ["llm-api-keys", "postgres-credentials"],
                "configmaps": [],
            },
        },
    },
}


# --- load_capabilities ---------------------------------------------------

def test_load_capabilities_accepts_well_formed_input(gen, tmp_path):
    path = tmp_path / "cap.yaml"
    path.write_text(yaml.safe_dump(MINIMAL_SPEC))
    spec = gen.load_capabilities(path)
    assert spec["namespace"] == "test-ns"
    assert "echo" in spec["agents"]


@pytest.mark.parametrize("missing_field", ["version", "namespace", "services", "agents"])
def test_load_capabilities_rejects_missing_required_fields(gen, tmp_path, missing_field):
    bad = {k: v for k, v in MINIMAL_SPEC.items() if k != missing_field}
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError, match=missing_field):
        gen.load_capabilities(path)


def test_load_capabilities_rejects_unsupported_version(gen, tmp_path):
    bad = dict(MINIMAL_SPEC, version=42)
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError, match="version"):
        gen.load_capabilities(path)


# --- build_network_policy -------------------------------------------------

def test_network_policy_basic_shape(gen):
    np = gen.build_network_policy("echo", MINIMAL_SPEC["agents"]["echo"], MINIMAL_SPEC)
    assert np["apiVersion"] == "networking.k8s.io/v1"
    assert np["kind"] == "NetworkPolicy"
    assert np["metadata"]["name"] == "echo-agent-egress"
    assert np["metadata"]["namespace"] == "test-ns"
    assert np["spec"]["podSelector"] == {"matchLabels": {"app": "echo-agent"}}
    assert np["spec"]["policyTypes"] == ["Egress"]


def test_network_policy_in_cluster_egress_has_correct_pod_selector_and_ports(gen):
    np = gen.build_network_policy("echo", MINIMAL_SPEC["agents"]["echo"], MINIMAL_SPEC)
    redis_rule = next(r for r in np["spec"]["egress"]
                      if r["to"] and r["to"][0].get("podSelector", {}).get("matchLabels", {}).get("app") == "redis")
    assert redis_rule["ports"] == [{"port": 6379, "protocol": "TCP"}]


def test_network_policy_external_egress_uses_ipblock_with_rfc1918_exception(gen):
    np = gen.build_network_policy(
        "orchestrator", MINIMAL_SPEC["agents"]["orchestrator"], MINIMAL_SPEC
    )
    external = next(r for r in np["spec"]["egress"]
                    if r["to"] and "ipBlock" in r["to"][0])
    block = external["to"][0]["ipBlock"]
    assert block["cidr"] == "0.0.0.0/0"
    # All three RFC 1918 ranges must be excluded so "external" doesn't
    # accidentally re-permit cluster-internal traffic.
    assert "10.0.0.0/8" in block["except"]
    assert "172.16.0.0/12" in block["except"]
    assert "192.168.0.0/16" in block["except"]
    assert external["ports"] == [{"port": 443, "protocol": "TCP"}]


def test_network_policy_dns_rule_uses_canonical_namespace_label_REGRESSION(gen):
    """Regression test for the Day 8 DNS-selector bug.

    The wrong selector was `name: kube-system` (not auto-applied by k8s).
    The correct selector since k8s 1.22 is `kubernetes.io/metadata.name`.
    """
    np = gen.build_network_policy("echo", MINIMAL_SPEC["agents"]["echo"], MINIMAL_SPEC)
    dns_rules = [
        r for r in np["spec"]["egress"]
        if any(p.get("port") == 53 for p in r.get("ports", []))
    ]
    assert dns_rules, "no DNS rule emitted; agents cannot resolve service names"
    dns = dns_rules[0]
    ns_selector = dns["to"][0]["namespaceSelector"]["matchLabels"]
    assert ns_selector == {"kubernetes.io/metadata.name": "kube-system"}, (
        f"DNS selector regressed: got {ns_selector!r}. "
        "Must be `kubernetes.io/metadata.name`, not the legacy `name` label."
    )


def test_network_policy_dns_rule_covers_both_tcp_and_udp(gen):
    """DNS needs UDP for normal lookups + TCP for responses >512 bytes."""
    np = gen.build_network_policy("echo", MINIMAL_SPEC["agents"]["echo"], MINIMAL_SPEC)
    dns_rule = next(
        r for r in np["spec"]["egress"]
        if any(p.get("port") == 53 for p in r.get("ports", []))
    )
    protocols = {p["protocol"] for p in dns_rule["ports"]}
    assert protocols == {"TCP", "UDP"}


def test_network_policy_rejects_unknown_service_reference(gen):
    bad_spec = {
        **MINIMAL_SPEC,
        "agents": {
            "rogue": {
                "pod_selector": {"app": "rogue"},
                "network": {"egress_allow": ["nonexistent-service"]},
                "rbac": {},
            }
        },
    }
    with pytest.raises(ValueError, match="nonexistent-service"):
        gen.build_network_policy("rogue", bad_spec["agents"]["rogue"], bad_spec)


def test_network_policy_rejects_unknown_external_reference(gen):
    bad_agent = {
        "pod_selector": {"app": "rogue"},
        "network": {"external_allow": ["openai"]},
        "rbac": {},
    }
    with pytest.raises(ValueError, match="openai"):
        gen.build_network_policy("rogue", bad_agent, MINIMAL_SPEC)


def test_network_policy_agent_with_no_egress_still_gets_dns(gen):
    """An agent with no egress_allow should still resolve in-cluster names."""
    silent_agent = {
        "pod_selector": {"app": "silent"},
        "network": {},
        "rbac": {},
    }
    np = gen.build_network_policy("silent", silent_agent, MINIMAL_SPEC)
    # Only DNS rule should be present.
    assert len(np["spec"]["egress"]) == 1
    assert any(p["port"] == 53 for p in np["spec"]["egress"][0]["ports"])


# --- build_rbac ----------------------------------------------------------

def test_rbac_emits_sa_role_rolebinding_triple(gen):
    docs = gen.build_rbac("echo", MINIMAL_SPEC["agents"]["echo"], MINIMAL_SPEC)
    kinds = [d["kind"] for d in docs]
    assert kinds == ["ServiceAccount", "Role", "RoleBinding"]


def test_rbac_naming_convention(gen):
    docs = gen.build_rbac("echo", MINIMAL_SPEC["agents"]["echo"], MINIMAL_SPEC)
    sa, role, binding = docs
    assert sa["metadata"]["name"] == "echo-agent-sa"
    assert role["metadata"]["name"] == "echo-agent-role"
    assert binding["metadata"]["name"] == "echo-agent-rolebinding"


def test_rbac_role_only_grants_get_list_on_named_resources(gen):
    docs = gen.build_rbac("echo", MINIMAL_SPEC["agents"]["echo"], MINIMAL_SPEC)
    _, role, _ = docs
    for rule in role["rules"]:
        assert set(rule["verbs"]) <= {"get", "list"}, (
            f"role grants verbs beyond get/list: {rule['verbs']}"
        )
        assert "resourceNames" in rule, (
            f"rule has no resourceNames (cluster-wide grant): {rule}"
        )


def test_rbac_secret_resource_names_are_sorted_for_determinism(gen):
    """Sorted ordering makes regenerated outputs byte-stable across runs."""
    docs = gen.build_rbac(
        "orchestrator", MINIMAL_SPEC["agents"]["orchestrator"], MINIMAL_SPEC
    )
    _, role, _ = docs
    secrets_rule = next(r for r in role["rules"] if r["resources"] == ["secrets"])
    assert secrets_rule["resourceNames"] == sorted(secrets_rule["resourceNames"])
    # MINIMAL_SPEC purposely lists ["llm-api-keys", "postgres-credentials"] in
    # already-sorted order; sort the input differently to actually exercise the sort.
    perturbed = dict(MINIMAL_SPEC["agents"]["orchestrator"])
    perturbed["rbac"] = {"secrets": ["postgres-credentials", "llm-api-keys"]}
    docs2 = gen.build_rbac("orchestrator", perturbed, MINIMAL_SPEC)
    _, role2, _ = docs2
    secrets_rule2 = next(r for r in role2["rules"] if r["resources"] == ["secrets"])
    assert secrets_rule2["resourceNames"] == ["llm-api-keys", "postgres-credentials"]


def test_rbac_agent_with_empty_secrets_emits_no_secrets_rule(gen):
    no_secrets_agent = {
        "pod_selector": {"app": "x"},
        "network": {},
        "rbac": {"secrets": [], "configmaps": ["x-config"]},
    }
    docs = gen.build_rbac("x", no_secrets_agent, MINIMAL_SPEC)
    _, role, _ = docs
    secret_rules = [r for r in role["rules"] if r["resources"] == ["secrets"]]
    assert secret_rules == []


def test_rbac_binding_subject_matches_sa(gen):
    docs = gen.build_rbac("echo", MINIMAL_SPEC["agents"]["echo"], MINIMAL_SPEC)
    sa, role, binding = docs
    assert binding["subjects"][0]["name"] == sa["metadata"]["name"]
    assert binding["subjects"][0]["namespace"] == sa["metadata"]["namespace"]
    assert binding["roleRef"]["name"] == role["metadata"]["name"]


# --- emit_yaml + generate -------------------------------------------------

def test_emit_yaml_is_deterministic(gen, tmp_path):
    """Same docs in -> identical bytes out across runs."""
    docs = [
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "a"}, "spec": {}},
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "b"}, "spec": {}},
    ]
    p1 = tmp_path / "out1.yaml"
    p2 = tmp_path / "out2.yaml"
    gen.emit_yaml(docs, p1, header="# header")
    gen.emit_yaml(docs, p2, header="# header")
    assert p1.read_bytes() == p2.read_bytes()


def test_emit_yaml_writes_separator_between_docs(gen, tmp_path):
    docs = [
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "a"}},
        {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "b"}},
    ]
    out = tmp_path / "x.yaml"
    gen.emit_yaml(docs, out, header="# h")
    text = out.read_text(encoding="utf-8")
    assert text.count("---") == 2  # one per document
    # And it must be valid multi-doc YAML.
    loaded = list(yaml.safe_load_all(text))
    assert [d for d in loaded if d is not None] == docs


def test_generate_end_to_end(gen, tmp_path):
    cap_path = tmp_path / "cap.yaml"
    cap_path.write_text(yaml.safe_dump(MINIMAL_SPEC))
    np_out = tmp_path / "np.yaml"
    rbac_out = tmp_path / "rbac.yaml"

    n_net, n_rbac = gen.generate(cap_path, np_out, rbac_out)

    assert n_net == 2                  # echo + orchestrator
    assert n_rbac == 2 * 3             # SA + Role + RoleBinding per agent

    # Outputs parse as valid multi-doc YAML.
    np_docs = [d for d in yaml.safe_load_all(np_out.read_text()) if d is not None]
    rbac_docs = [d for d in yaml.safe_load_all(rbac_out.read_text()) if d is not None]
    assert [d["kind"] for d in np_docs] == ["NetworkPolicy", "NetworkPolicy"]
    assert {d["kind"] for d in rbac_docs} == {"ServiceAccount", "Role", "RoleBinding"}


def test_generate_is_idempotent(gen, tmp_path):
    """Re-running with the same input produces byte-identical files."""
    cap_path = tmp_path / "cap.yaml"
    cap_path.write_text(yaml.safe_dump(MINIMAL_SPEC))
    np1 = tmp_path / "np1.yaml"
    rbac1 = tmp_path / "rbac1.yaml"
    np2 = tmp_path / "np2.yaml"
    rbac2 = tmp_path / "rbac2.yaml"

    gen.generate(cap_path, np1, rbac1)
    gen.generate(cap_path, np2, rbac2)

    assert np1.read_bytes() == np2.read_bytes()
    assert rbac1.read_bytes() == rbac2.read_bytes()


def test_generate_orders_agents_alphabetically(gen, tmp_path):
    """Deterministic agent ordering — capabilities.yaml dict-order can't leak."""
    cap_path = tmp_path / "cap.yaml"
    cap_path.write_text(yaml.safe_dump(MINIMAL_SPEC))
    np_out = tmp_path / "np.yaml"
    rbac_out = tmp_path / "rbac.yaml"
    gen.generate(cap_path, np_out, rbac_out)

    np_docs = [d for d in yaml.safe_load_all(np_out.read_text()) if d is not None]
    names = [d["metadata"]["name"] for d in np_docs]
    # MINIMAL_SPEC has echo, orchestrator — alphabetical order.
    assert names == sorted(names)


# --- live repo capabilities.yaml smoke ------------------------------------

def test_repo_capabilities_yaml_generates_without_error(gen):
    """The real infrastructure/security/capabilities.yaml must round-trip
    through the generator without error. Catches drift between the matrix
    and the generator's expectations."""
    repo_root = _GENERATOR_PATH.parents[2]
    cap_path = repo_root / "infrastructure" / "security" / "capabilities.yaml"
    if not cap_path.is_file():
        pytest.skip("repo capabilities.yaml missing (test only valid in this repo)")
    spec = gen.load_capabilities(cap_path)
    for name, agent in spec["agents"].items():
        gen.build_network_policy(name, agent, spec)
        gen.build_rbac(name, agent, spec)
