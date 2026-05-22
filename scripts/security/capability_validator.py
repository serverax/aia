"""Validates capabilities.yaml semantics beyond what generate_policies does.

`generate_policies.load_capabilities` checks structural things (required
top-level fields, version). This module checks semantic correctness:
references resolve, names are valid k8s, no agent is mis-configured to
the point that it can't function.

The validator returns a list of `ValidationFinding`s with severity. It
does NOT raise — the caller decides what to do based on aggregate severity
(see `pre_deploy_check.sh`).

Used by:
  * `scripts/security/pre_deploy_check.sh` — deploy gate
  * standalone:  `python -m scripts.security.capability_validator <path>`

Exit codes when run as CLI:
  0  no critical findings (warnings may be present)
  1  at least one critical finding
  2  invocation error (file missing, unparseable)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


# K8s object name regex per RFC 1123 (DNS label). 63 char max for namespaces,
# but the underlying validation is what k8s itself enforces — keep parity.
_K8S_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
_MAX_K8S_NAME_LEN = 63


@dataclass
class ValidationFinding:
    severity: str       # "critical" | "warning" | "info"
    code: str           # short symbolic code, e.g. "UNDEFINED_SERVICE"
    message: str        # human-readable, includes the offending value
    location: str       # YAML path, e.g. "agents.echo.network.egress_allow"


def validate(spec: dict[str, Any]) -> list[ValidationFinding]:
    """Run all semantic checks against a parsed capabilities.yaml dict.

    Returns a list of findings sorted by severity (critical first), then
    by code. Empty list = clean.
    """
    findings: list[ValidationFinding] = []

    findings.extend(_check_version(spec))
    findings.extend(_check_namespace(spec))
    findings.extend(_check_services_block(spec))
    findings.extend(_check_external_block(spec))
    findings.extend(_check_agents(spec))

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: (severity_order.get(f.severity, 99), f.code, f.location))
    return findings


# ---- individual checks ---------------------------------------------------

def _check_version(spec: dict[str, Any]) -> list[ValidationFinding]:
    if "version" not in spec:
        return [ValidationFinding(
            "critical", "MISSING_VERSION",
            "capabilities.yaml has no `version` field",
            "version",
        )]
    if spec["version"] != 1:
        return [ValidationFinding(
            "critical", "UNSUPPORTED_VERSION",
            f"unsupported version: {spec['version']} (only `1` is currently supported)",
            "version",
        )]
    return []


def _check_namespace(spec: dict[str, Any]) -> list[ValidationFinding]:
    ns = spec.get("namespace")
    if not ns:
        return [ValidationFinding(
            "critical", "MISSING_NAMESPACE",
            "capabilities.yaml has no `namespace` field",
            "namespace",
        )]
    if not isinstance(ns, str):
        return [ValidationFinding(
            "critical", "NAMESPACE_NOT_STRING",
            f"namespace must be a string, got {type(ns).__name__}",
            "namespace",
        )]
    if len(ns) > _MAX_K8S_NAME_LEN:
        return [ValidationFinding(
            "critical", "NAMESPACE_TOO_LONG",
            f"namespace `{ns}` exceeds {_MAX_K8S_NAME_LEN}-char k8s limit",
            "namespace",
        )]
    if not _K8S_NAME_RE.match(ns):
        return [ValidationFinding(
            "critical", "INVALID_NAMESPACE_NAME",
            f"namespace `{ns}` is not a valid k8s DNS label "
            "(lowercase letters, digits, hyphens; can't start/end with hyphen)",
            "namespace",
        )]
    return []


def _check_services_block(spec: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    services = spec.get("services") or {}
    if not isinstance(services, dict):
        return [ValidationFinding(
            "critical", "SERVICES_NOT_DICT",
            f"`services` must be a dict, got {type(services).__name__}",
            "services",
        )]
    for name, svc in services.items():
        loc = f"services.{name}"
        if not _K8S_NAME_RE.match(name):
            findings.append(ValidationFinding(
                "critical", "INVALID_SERVICE_NAME",
                f"service key `{name}` is not a valid k8s name",
                loc,
            ))
        if not isinstance(svc, dict):
            findings.append(ValidationFinding(
                "critical", "SERVICE_NOT_DICT",
                f"service `{name}` must be a dict",
                loc,
            ))
            continue
        if not svc.get("selector"):
            findings.append(ValidationFinding(
                "critical", "MISSING_SELECTOR",
                f"service `{name}` has no `selector`",
                f"{loc}.selector",
            ))
        ports = svc.get("ports") or []
        if not ports:
            findings.append(ValidationFinding(
                "warning", "SERVICE_NO_PORTS",
                f"service `{name}` declares no ports — egress rules referencing it will be wide-open",
                f"{loc}.ports",
            ))
        for i, port_spec in enumerate(ports):
            if not isinstance(port_spec, dict) or "port" not in port_spec:
                findings.append(ValidationFinding(
                    "critical", "INVALID_PORT_ENTRY",
                    f"service `{name}` port[{i}] missing `port` field",
                    f"{loc}.ports[{i}]",
                ))
                continue
            p = port_spec["port"]
            if not isinstance(p, int) or not (1 <= p <= 65535):
                findings.append(ValidationFinding(
                    "critical", "PORT_OUT_OF_RANGE",
                    f"service `{name}` port[{i}] = {p} is not a valid TCP/UDP port",
                    f"{loc}.ports[{i}].port",
                ))
            proto = port_spec.get("protocol", "TCP")
            if proto not in {"TCP", "UDP", "SCTP"}:
                findings.append(ValidationFinding(
                    "critical", "INVALID_PROTOCOL",
                    f"service `{name}` port[{i}] protocol `{proto}` is not TCP/UDP/SCTP",
                    f"{loc}.ports[{i}].protocol",
                ))
    return findings


def _check_external_block(spec: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    external = spec.get("external") or {}
    if not isinstance(external, dict):
        return [ValidationFinding(
            "critical", "EXTERNAL_NOT_DICT",
            f"`external` must be a dict, got {type(external).__name__}",
            "external",
        )]
    for name, ext in external.items():
        loc = f"external.{name}"
        if not isinstance(ext, dict):
            findings.append(ValidationFinding(
                "critical", "EXTERNAL_NOT_DICT",
                f"external `{name}` must be a dict",
                loc,
            ))
            continue
        if not ext.get("ports"):
            findings.append(ValidationFinding(
                "warning", "EXTERNAL_NO_PORTS",
                f"external `{name}` declares no ports — agents using it will get wide-open egress",
                f"{loc}.ports",
            ))
    return findings


def _check_agents(spec: dict[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    agents = spec.get("agents") or {}
    if not isinstance(agents, dict):
        return [ValidationFinding(
            "critical", "AGENTS_NOT_DICT",
            f"`agents` must be a dict, got {type(agents).__name__}",
            "agents",
        )]
    if not agents:
        findings.append(ValidationFinding(
            "warning", "NO_AGENTS",
            "no agents declared — generator will produce empty output",
            "agents",
        ))
        return findings

    services = set((spec.get("services") or {}).keys())
    externals = set((spec.get("external") or {}).keys())

    for name, agent in agents.items():
        loc = f"agents.{name}"
        if not _K8S_NAME_RE.match(name):
            findings.append(ValidationFinding(
                "critical", "INVALID_AGENT_NAME",
                f"agent key `{name}` is not a valid k8s name (used in SA/Role names)",
                loc,
            ))
        if not isinstance(agent, dict):
            findings.append(ValidationFinding(
                "critical", "AGENT_NOT_DICT",
                f"agent `{name}` must be a dict",
                loc,
            ))
            continue
        if not agent.get("pod_selector"):
            findings.append(ValidationFinding(
                "critical", "EMPTY_POD_SELECTOR",
                f"agent `{name}` has no `pod_selector` — generated NetworkPolicy will match every pod in the namespace",
                f"{loc}.pod_selector",
            ))

        network = agent.get("network") or {}
        egress = network.get("egress_allow") or []
        for svc in egress:
            if svc not in services:
                findings.append(ValidationFinding(
                    "critical", "UNDEFINED_SERVICE",
                    f"agent `{name}` references undefined service `{svc}` (not in services block)",
                    f"{loc}.network.egress_allow",
                ))
        external_allow = network.get("external_allow") or []
        for ext in external_allow:
            if ext not in externals:
                findings.append(ValidationFinding(
                    "critical", "UNDEFINED_EXTERNAL",
                    f"agent `{name}` references undefined external `{ext}` (not in external block)",
                    f"{loc}.network.external_allow",
                ))

        if not egress and not external_allow:
            findings.append(ValidationFinding(
                "warning", "AGENT_NO_EGRESS",
                f"agent `{name}` has no egress_allow or external_allow — will only reach kube-dns (rule auto-added) and nothing else; verify intent",
                f"{loc}.network",
            ))

        rbac = agent.get("rbac") or {}
        if not (rbac.get("secrets") or rbac.get("configmaps")):
            findings.append(ValidationFinding(
                "info", "AGENT_NO_RBAC",
                f"agent `{name}` requests no secrets or configmaps — generated Role will have zero rules (legal but unusual)",
                f"{loc}.rbac",
            ))

    return findings


# ---- CLI -----------------------------------------------------------------

def _summarise(findings: list[ValidationFinding]) -> dict[str, int]:
    out = {"critical": 0, "warning": 0, "info": 0}
    for f in findings:
        out[f.severity] = out.get(f.severity, 0) + 1
    return out


def _emit_text(findings: list[ValidationFinding]) -> str:
    if not findings:
        return "OK: capabilities.yaml passes all semantic checks"
    lines = []
    for f in findings:
        lines.append(f"[{f.severity.upper():<8}] {f.code:<25} {f.location}")
        lines.append(f"           {f.message}")
    summary = _summarise(findings)
    lines.append("")
    lines.append(f"Total: {summary['critical']} critical, "
                 f"{summary['warning']} warning, {summary['info']} info")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "capabilities",
        nargs="?",
        default="infrastructure/security/capabilities.yaml",
        type=Path,
    )
    parser.add_argument("--json", action="store_true",
                        help="emit JSON instead of text")
    args = parser.parse_args(argv)

    if not args.capabilities.is_file():
        print(f"ERROR: {args.capabilities} not found", file=sys.stderr)
        return 2
    try:
        spec = yaml.safe_load(args.capabilities.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        print(f"ERROR: cannot parse YAML: {exc}", file=sys.stderr)
        return 2

    findings = validate(spec)

    if args.json:
        print(json.dumps({
            "findings": [asdict(f) for f in findings],
            "summary": _summarise(findings),
        }, indent=2))
    else:
        print(_emit_text(findings))

    return 1 if any(f.severity == "critical" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
