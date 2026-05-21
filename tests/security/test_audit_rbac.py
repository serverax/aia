"""Unit tests for scripts/security/audit_rbac.py.

Mock kubectl JSON output drives every branch:
  - MISSING: capabilities expects a SA that isn't there
  - EXTRA: cluster has a SA that capabilities doesn't declare
  - MISMATCH (Role): rule verbs differ
  - MISMATCH (RoleBinding): subjects differ
  - PASS: identical state -> no findings
  - Generic agent-sa from namespace.yaml is allowlisted, not flagged as EXTRA
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.security import audit_rbac, generate_policies

pytestmark = [pytest.mark.unit]


SPEC = {
    "version": 1,
    "namespace": "test-ns",
    "services": {
        "redis": {"selector": {"app": "redis"}, "ports": [{"port": 6379, "protocol": "TCP"}]},
    },
    "agents": {
        "echo": {
            "pod_selector": {"app": "echo-agent"},
            "network": {"egress_allow": ["redis"]},
            "rbac": {
                "secrets": ["postgres-credentials"],
                "configmaps": ["echo-agent-config"],
            },
        },
    },
}


@pytest.fixture
def capabilities_path(tmp_path) -> Path:
    p = tmp_path / "cap.yaml"
    p.write_text(yaml.safe_dump(SPEC))
    return p


def _kubectl_items(*docs: dict[str, Any]) -> dict[str, Any]:
    return {"apiVersion": "v1", "kind": "List", "items": list(docs)}


def _expected_docs(spec: dict[str, Any]) -> dict[str, Any]:
    """Helper to produce the SA/Role/RoleBinding the generator would emit."""
    agent_name = next(iter(spec["agents"]))
    docs = generate_policies.build_rbac(agent_name, spec["agents"][agent_name], spec)
    return {d["kind"]: d for d in docs}


# --- happy path ---------------------------------------------------------

def test_no_findings_when_cluster_matches_capabilities(capabilities_path):
    expected = audit_rbac.expected_state(capabilities_path)
    cluster = _kubectl_items(
        *expected["ServiceAccount"].values(),
        *expected["Role"].values(),
        *expected["RoleBinding"].values(),
    )
    actual = audit_rbac.actual_state(cluster)
    assert audit_rbac.audit(expected, actual) == []


# --- MISSING ------------------------------------------------------------

def test_missing_serviceaccount_is_error(capabilities_path):
    expected = audit_rbac.expected_state(capabilities_path)
    # Cluster has nothing.
    actual = audit_rbac.actual_state(_kubectl_items())
    findings = audit_rbac.audit(expected, actual)
    sa_findings = [f for f in findings if f.resource == "ServiceAccount"]
    assert len(sa_findings) == 1
    assert sa_findings[0].kind == "MISSING"
    assert sa_findings[0].severity == audit_rbac.Severity.ERROR
    assert sa_findings[0].name == "echo-agent-sa"


def test_missing_role_is_error(capabilities_path):
    expected = audit_rbac.expected_state(capabilities_path)
    # Cluster has only the SA, not the Role.
    actual = audit_rbac.actual_state(_kubectl_items(
        *expected["ServiceAccount"].values()
    ))
    findings = audit_rbac.audit(expected, actual)
    role_findings = [f for f in findings if f.resource == "Role"]
    assert len(role_findings) == 1
    assert role_findings[0].kind == "MISSING"
    assert role_findings[0].name == "echo-agent-role"


# --- EXTRA --------------------------------------------------------------

def test_extra_serviceaccount_is_warning(capabilities_path):
    expected = audit_rbac.expected_state(capabilities_path)
    rogue_sa = {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": {"name": "rogue-sa", "namespace": "test-ns"},
    }
    actual = audit_rbac.actual_state(_kubectl_items(
        *expected["ServiceAccount"].values(),
        *expected["Role"].values(),
        *expected["RoleBinding"].values(),
        rogue_sa,
    ))
    findings = audit_rbac.audit(expected, actual)
    extras = [f for f in findings if f.kind == "EXTRA"]
    assert len(extras) == 1
    assert extras[0].name == "rogue-sa"
    assert extras[0].severity == audit_rbac.Severity.WARNING


def test_generic_agent_sa_is_not_flagged_as_extra(capabilities_path):
    """`agent-sa` lives in namespace.yaml (not per-agent); allowlisted."""
    expected = audit_rbac.expected_state(capabilities_path)
    generic_sa = {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": {"name": "agent-sa", "namespace": "test-ns"},
    }
    actual = audit_rbac.actual_state(_kubectl_items(
        *expected["ServiceAccount"].values(),
        *expected["Role"].values(),
        *expected["RoleBinding"].values(),
        generic_sa,
    ))
    findings = audit_rbac.audit(expected, actual)
    assert not any(f.name == "agent-sa" for f in findings)


def test_default_serviceaccount_is_not_flagged(capabilities_path):
    """Every namespace has a `default` SA; never flag it."""
    expected = audit_rbac.expected_state(capabilities_path)
    default_sa = {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": {"name": "default", "namespace": "test-ns"},
    }
    actual = audit_rbac.actual_state(_kubectl_items(
        *expected["ServiceAccount"].values(),
        *expected["Role"].values(),
        *expected["RoleBinding"].values(),
        default_sa,
    ))
    findings = audit_rbac.audit(expected, actual)
    assert not any(f.name == "default" for f in findings)


# --- MISMATCH -----------------------------------------------------------

def test_role_with_extra_verb_is_mismatch_error(capabilities_path):
    """An attacker (or careless admin) adds 'create' to a Role; detect it."""
    expected = audit_rbac.expected_state(capabilities_path)
    docs = _expected_docs(SPEC)
    tampered_role = json.loads(json.dumps(docs["Role"]))   # deep-ish copy
    # Append 'create' verb to the first rule.
    tampered_role["rules"][0]["verbs"].append("create")

    actual = audit_rbac.actual_state(_kubectl_items(
        docs["ServiceAccount"],
        tampered_role,
        docs["RoleBinding"],
    ))
    findings = audit_rbac.audit(expected, actual)
    mismatches = [f for f in findings if f.kind == "MISMATCH" and f.resource == "Role"]
    assert len(mismatches) == 1
    assert mismatches[0].severity == audit_rbac.Severity.ERROR
    assert "unexpected rule" in mismatches[0].detail or "create" in mismatches[0].detail


def test_role_missing_rule_is_mismatch(capabilities_path):
    """A rule was deleted out from under the deployment."""
    expected = audit_rbac.expected_state(capabilities_path)
    docs = _expected_docs(SPEC)
    stripped_role = json.loads(json.dumps(docs["Role"]))
    stripped_role["rules"] = stripped_role["rules"][:1]   # keep only first rule

    actual = audit_rbac.actual_state(_kubectl_items(
        docs["ServiceAccount"],
        stripped_role,
        docs["RoleBinding"],
    ))
    findings = audit_rbac.audit(expected, actual)
    mismatches = [f for f in findings if f.kind == "MISMATCH"]
    assert any("missing rule" in m.detail for m in mismatches)


def test_rolebinding_subject_drift_is_mismatch(capabilities_path):
    """Subjects were swapped (or pointed at a different SA)."""
    expected = audit_rbac.expected_state(capabilities_path)
    docs = _expected_docs(SPEC)
    tampered_binding = json.loads(json.dumps(docs["RoleBinding"]))
    tampered_binding["subjects"][0]["name"] = "other-sa"

    actual = audit_rbac.actual_state(_kubectl_items(
        docs["ServiceAccount"],
        docs["Role"],
        tampered_binding,
    ))
    findings = audit_rbac.audit(expected, actual)
    mismatches = [f for f in findings if f.resource == "RoleBinding" and f.kind == "MISMATCH"]
    assert len(mismatches) == 1
    assert "subjects differ" in mismatches[0].detail


def test_rolebinding_roleref_drift_is_mismatch(capabilities_path):
    expected = audit_rbac.expected_state(capabilities_path)
    docs = _expected_docs(SPEC)
    tampered = json.loads(json.dumps(docs["RoleBinding"]))
    tampered["roleRef"]["name"] = "some-other-role"

    actual = audit_rbac.actual_state(_kubectl_items(
        docs["ServiceAccount"],
        docs["Role"],
        tampered,
    ))
    findings = audit_rbac.audit(expected, actual)
    mismatches = [f for f in findings if f.resource == "RoleBinding"]
    assert any("roleRef differs" in m.detail for m in mismatches)


# --- main() CLI ---------------------------------------------------------

def test_main_returns_0_on_match(tmp_path, capabilities_path, capsys):
    expected = audit_rbac.expected_state(capabilities_path)
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(_kubectl_items(
        *expected["ServiceAccount"].values(),
        *expected["Role"].values(),
        *expected["RoleBinding"].values(),
    )))
    rc = audit_rbac.main([
        "--capabilities", str(capabilities_path),
        "--from-json", str(state_path),
        "--quiet",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK: deployed RBAC matches" in out


def test_main_returns_1_on_drift(tmp_path, capabilities_path, capsys):
    # Cluster is empty -> everything missing.
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(_kubectl_items()))
    rc = audit_rbac.main([
        "--capabilities", str(capabilities_path),
        "--from-json", str(state_path),
        "--quiet",
    ])
    assert rc == 1
    out = capsys.readouterr().out
    assert "MISSING" in out
    assert "DRIFT" in out


def test_main_returns_2_when_capabilities_missing(tmp_path, capsys):
    rc = audit_rbac.main([
        "--capabilities", str(tmp_path / "does-not-exist.yaml"),
        "--from-json", str(tmp_path),  # irrelevant
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "not found" in err


def test_main_returns_2_when_json_unreadable(tmp_path, capabilities_path, capsys):
    rc = audit_rbac.main([
        "--capabilities", str(capabilities_path),
        "--from-json", str(tmp_path / "missing.json"),
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "could not load" in err


# --- Finding.format -----------------------------------------------------

def test_finding_format_contains_all_parts():
    f = audit_rbac.Finding(
        kind="MISSING",
        resource="Role",
        name="echo-agent-role",
        severity=audit_rbac.Severity.ERROR,
        detail="capabilities.yaml requires it",
        remediation="kubectl apply",
    )
    text = f.format()
    assert "ERROR" in text
    assert "MISSING" in text
    assert "Role/echo-agent-role" in text
    assert "fix:" in text
