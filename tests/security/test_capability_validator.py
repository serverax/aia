"""Unit tests for scripts/security/capability_validator.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.security import capability_validator as cv

pytestmark = [pytest.mark.unit]


def _good_spec() -> dict:
    """A fully-valid spec mirror used as a baseline; tests mutate copies."""
    return {
        "version": 1,
        "namespace": "ordinox-ai",
        "services": {
            "redis": {
                "selector": {"app": "redis"},
                "ports": [{"port": 6379, "protocol": "TCP"}],
            },
        },
        "external": {
            "anthropic": {"ports": [{"port": 443, "protocol": "TCP"}]},
        },
        "agents": {
            "echo": {
                "pod_selector": {"app": "echo-agent"},
                "network": {"egress_allow": ["redis"]},
                "rbac": {"secrets": ["postgres-credentials"]},
            },
        },
    }


# ---- structural / version ------------------------------------------------

def test_clean_spec_returns_no_findings():
    assert cv.validate(_good_spec()) == []


def test_missing_version_is_critical():
    spec = _good_spec()
    del spec["version"]
    findings = cv.validate(spec)
    assert any(f.code == "MISSING_VERSION" and f.severity == "critical" for f in findings)


def test_unsupported_version_is_critical():
    spec = _good_spec()
    spec["version"] = 42
    findings = cv.validate(spec)
    assert any(f.code == "UNSUPPORTED_VERSION" for f in findings)


# ---- namespace -----------------------------------------------------------

def test_missing_namespace_is_critical():
    spec = _good_spec()
    del spec["namespace"]
    findings = cv.validate(spec)
    assert any(f.code == "MISSING_NAMESPACE" for f in findings)


def test_namespace_with_uppercase_rejected():
    spec = _good_spec()
    spec["namespace"] = "Ordinox-AI"
    findings = cv.validate(spec)
    assert any(f.code == "INVALID_NAMESPACE_NAME" for f in findings)


def test_namespace_starting_with_hyphen_rejected():
    spec = _good_spec()
    spec["namespace"] = "-bad-name"
    findings = cv.validate(spec)
    assert any(f.code == "INVALID_NAMESPACE_NAME" for f in findings)


def test_namespace_over_63_chars_rejected():
    spec = _good_spec()
    spec["namespace"] = "a" * 64
    findings = cv.validate(spec)
    assert any(f.code == "NAMESPACE_TOO_LONG" for f in findings)


# ---- services block ------------------------------------------------------

def test_service_with_invalid_port_number_critical():
    spec = _good_spec()
    spec["services"]["redis"]["ports"] = [{"port": 99999, "protocol": "TCP"}]
    findings = cv.validate(spec)
    assert any(f.code == "PORT_OUT_OF_RANGE" for f in findings)


def test_service_with_unknown_protocol_critical():
    spec = _good_spec()
    spec["services"]["redis"]["ports"] = [{"port": 6379, "protocol": "ICMP"}]
    findings = cv.validate(spec)
    assert any(f.code == "INVALID_PROTOCOL" for f in findings)


def test_service_missing_selector_critical():
    spec = _good_spec()
    del spec["services"]["redis"]["selector"]
    findings = cv.validate(spec)
    assert any(f.code == "MISSING_SELECTOR" for f in findings)


def test_service_with_no_ports_warning():
    spec = _good_spec()
    spec["services"]["redis"]["ports"] = []
    findings = cv.validate(spec)
    assert any(f.code == "SERVICE_NO_PORTS" and f.severity == "warning" for f in findings)


# ---- agents block --------------------------------------------------------

def test_agent_with_undefined_service_reference_critical():
    spec = _good_spec()
    spec["agents"]["echo"]["network"]["egress_allow"] = ["nonexistent"]
    findings = cv.validate(spec)
    matching = [f for f in findings if f.code == "UNDEFINED_SERVICE"]
    assert len(matching) == 1
    assert "nonexistent" in matching[0].message


def test_agent_with_undefined_external_reference_critical():
    spec = _good_spec()
    spec["agents"]["echo"]["network"]["external_allow"] = ["openai"]
    findings = cv.validate(spec)
    assert any(f.code == "UNDEFINED_EXTERNAL" for f in findings)


def test_agent_with_empty_pod_selector_critical():
    spec = _good_spec()
    spec["agents"]["echo"]["pod_selector"] = {}
    findings = cv.validate(spec)
    assert any(f.code == "EMPTY_POD_SELECTOR" for f in findings)


def test_agent_with_no_egress_emits_warning():
    spec = _good_spec()
    spec["agents"]["echo"]["network"] = {}
    findings = cv.validate(spec)
    assert any(f.code == "AGENT_NO_EGRESS" and f.severity == "warning" for f in findings)


def test_agent_with_invalid_name_critical():
    spec = _good_spec()
    spec["agents"]["Bad_Name"] = spec["agents"].pop("echo")
    findings = cv.validate(spec)
    assert any(f.code == "INVALID_AGENT_NAME" for f in findings)


def test_findings_sorted_critical_first():
    """Findings list returns criticals before warnings, in stable order."""
    spec = _good_spec()
    spec["services"]["redis"]["ports"] = []           # warning
    spec["agents"]["echo"]["network"]["egress_allow"] = ["bogus"]   # critical
    findings = cv.validate(spec)
    severities = [f.severity for f in findings]
    # All criticals come first
    crit_count = severities.count("critical")
    assert severities[:crit_count] == ["critical"] * crit_count


# ---- CLI -----------------------------------------------------------------

def test_cli_returns_0_on_clean_spec(tmp_path, capsys):
    path = tmp_path / "cap.yaml"
    path.write_text(yaml.safe_dump(_good_spec()))
    rc = cv.main([str(path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_cli_returns_1_on_critical_finding(tmp_path, capsys):
    spec = _good_spec()
    spec["agents"]["echo"]["network"]["egress_allow"] = ["bogus"]
    path = tmp_path / "cap.yaml"
    path.write_text(yaml.safe_dump(spec))
    rc = cv.main([str(path)])
    assert rc == 1
    assert "UNDEFINED_SERVICE" in capsys.readouterr().out


def test_cli_returns_0_on_warning_only(tmp_path, capsys):
    """Warnings don't block; only criticals do."""
    spec = _good_spec()
    spec["services"]["redis"]["ports"] = []   # warning
    path = tmp_path / "cap.yaml"
    path.write_text(yaml.safe_dump(spec))
    rc = cv.main([str(path)])
    assert rc == 0


def test_cli_returns_2_on_missing_file(tmp_path, capsys):
    rc = cv.main([str(tmp_path / "does-not-exist.yaml")])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_cli_returns_2_on_malformed_yaml(tmp_path, capsys):
    path = tmp_path / "bad.yaml"
    path.write_text("{not: valid: yaml::")
    rc = cv.main([str(path)])
    assert rc == 2


def test_cli_json_output_parseable(tmp_path, capsys):
    spec = _good_spec()
    spec["agents"]["echo"]["network"]["egress_allow"] = ["bogus"]
    path = tmp_path / "cap.yaml"
    path.write_text(yaml.safe_dump(spec))
    cv.main([str(path), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "findings" in payload
    assert payload["summary"]["critical"] >= 1
    assert any(f["code"] == "UNDEFINED_SERVICE" for f in payload["findings"])


def test_real_repo_capabilities_passes(tmp_path):
    """Smoke test against the actual capabilities.yaml in the repo."""
    repo_cap = Path(__file__).resolve().parents[2] / "infrastructure" / "security" / "capabilities.yaml"
    if not repo_cap.is_file():
        pytest.skip("repo capabilities.yaml missing")
    spec = yaml.safe_load(repo_cap.read_text(encoding="utf-8"))
    findings = cv.validate(spec)
    criticals = [f for f in findings if f.severity == "critical"]
    assert criticals == [], (
        f"real capabilities.yaml has critical issues — fix before deploying:\n"
        + "\n".join(f"  {f.code} @ {f.location}: {f.message}" for f in criticals)
    )
