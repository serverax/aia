"""Integration tests for scripts/security/pre_deploy_check.sh.

Each test drives the bash script via subprocess and asserts against:
  * exit code (0 GO / 1 NO-GO / 2 ERROR)
  * JSON report schema + key contents
  * Specific checks pass/fail as expected

Tests use the real repo files unless explicitly overriding `CAPABILITIES`
via env var, because the gate is meant to validate the actual deployment
artifacts. Tests that need to inject broken state copy the real files
into a tmp_path first and point CAPABILITIES at the tampered copy.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.unit]


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "security" / "pre_deploy_check.sh"
REAL_CAPABILITIES = REPO_ROOT / "infrastructure" / "security" / "capabilities.yaml"


def _find_bash() -> str | None:
    """Pick a real Bourne-shell-compatible bash.

    On Windows the bare `bash` from PATH can resolve to WSL bash
    (`C:\\Windows\\System32\\bash.exe`) which fails on the script's MSYS
    path conventions. Prefer Git Bash if present.
    """
    candidates = [
        "C:/Program Files/Git/usr/bin/bash.exe",
        "C:/Program Files (x86)/Git/usr/bin/bash.exe",
        "/usr/bin/bash",
        "/bin/bash",
    ]
    for c in candidates:
        if Path(c).is_file():
            return c
    return shutil.which("bash")


BASH = _find_bash()


def _python_for_subprocess() -> str:
    """Return a Python the bash script can actually invoke.

    On Windows the bare `python` resolves to the Microsoft Store shim,
    so we pass `sys.executable` directly. Git Bash refuses to invoke
    Windows-style `C:\\path\\python.exe`, so convert to MSYS form first.
    """
    return _msys_path(sys.executable)


def _msys_path(p: Path | str) -> str:
    """Convert C:\\foo\\bar to /c/foo/bar for Git Bash.

    Has no effect on non-Windows paths.
    """
    s = str(p).replace("\\", "/")
    if len(s) >= 2 and s[1] == ":":
        s = "/" + s[0].lower() + s[2:]
    return s


def _run_gate(
    *args: str,
    env_overrides: dict[str, str] | None = None,
    report_path: Path | None = None,
) -> tuple[int, str, str, dict]:
    """Run the gate. Returns (rc, stdout, stderr, json_report_dict)."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["PYTHON"] = _python_for_subprocess()
    if report_path is None:
        # Each test gets its own report file so parallel runs don't collide.
        report_path = Path(tempfile.gettempdir()) / f"gate-{os.getpid()}-{id(args)}-report.json"
    if report_path.exists():
        report_path.unlink()
    # Pass MSYS-style path so bash inside Git Bash can resolve it.
    env["REPORT_FILE"] = _msys_path(report_path)
    if env_overrides:
        env.update(env_overrides)

    if BASH is None:
        pytest.skip("no usable bash found")
    result = subprocess.run(
        [BASH, str(GATE_SCRIPT), *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    report = {}
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    return result.returncode, result.stdout, result.stderr, report


# ----------------------------------------------------------------- #
# 1. Happy path
# ----------------------------------------------------------------- #

def test_clean_repo_returns_go_verdict():
    """Against the real repo state, the gate should report GO."""
    if not GATE_SCRIPT.is_file():
        pytest.skip("gate script not present")
    if BASH is None:
        pytest.skip("no usable bash found")

    rc, out, _, report = _run_gate("--quiet")
    assert rc == 0, f"expected GO (rc=0), got rc={rc}\nstdout:\n{out}"
    assert report["verdict"] == "GO"
    assert report["summary"]["critical"] == 0


def test_report_schema_has_required_top_level_fields():
    rc, _, _, report = _run_gate("--quiet")
    for key in ("timestamp", "mode", "verdict", "exit_code", "summary", "checks"):
        assert key in report, f"missing top-level key: {key}"
    for sev_key in ("critical", "warning", "info"):
        assert sev_key in report["summary"], f"summary missing {sev_key}"


def test_every_check_recorded_in_report():
    """All four offline checks must appear in the report."""
    _, _, _, report = _run_gate("--quiet")
    check_names = {c["check"] for c in report["checks"]}
    expected = {
        "capability_validator",
        "generator_drift",
        "policy_runtime_tests",
        "manifest_dry_run",
        "rbac_audit",
    }
    assert expected <= check_names, f"missing checks: {expected - check_names}"


def test_rbac_audit_skipped_in_offline_mode():
    _, _, _, report = _run_gate("--quiet")
    rbac = next(c for c in report["checks"] if c["check"] == "rbac_audit")
    assert rbac["status"] == "SKIP"
    assert rbac["severity"] == "info"
    assert "offline" in rbac["message"].lower()


# ----------------------------------------------------------------- #
# 2. Failure injection — capability validator
# ----------------------------------------------------------------- #

@pytest.fixture
def broken_capabilities(tmp_path) -> Path:
    """Copy real capabilities.yaml then inject an undefined-service ref."""
    spec = yaml.safe_load(REAL_CAPABILITIES.read_text(encoding="utf-8"))
    # Force a critical finding: agent references a service that doesn't exist.
    first_agent = next(iter(spec["agents"]))
    spec["agents"][first_agent]["network"].setdefault("egress_allow", []).append("does-not-exist")
    bad = tmp_path / "capabilities-bad.yaml"
    bad.write_text(yaml.safe_dump(spec))
    return bad


def test_undefined_service_ref_blocks_deploy(broken_capabilities):
    rc, _, _, report = _run_gate(
        "--quiet",
        env_overrides={"CAPABILITIES": str(broken_capabilities)},
    )
    assert rc == 1, f"expected NO-GO (rc=1), got rc={rc}"
    assert report["verdict"] == "NO-GO"
    cap_check = next(c for c in report["checks"] if c["check"] == "capability_validator")
    assert cap_check["status"] == "FAIL"
    assert cap_check["severity"] == "critical"


def test_missing_capabilities_file_fails_critically(tmp_path):
    rc, _, _, report = _run_gate(
        "--quiet",
        env_overrides={"CAPABILITIES": str(tmp_path / "nope.yaml")},
    )
    assert rc == 1
    cap_check = next(c for c in report["checks"] if c["check"] == "capability_validator")
    assert "not found" in cap_check["message"].lower()


# ----------------------------------------------------------------- #
# 3. Failure injection — generator drift
# ----------------------------------------------------------------- #

@pytest.fixture
def drift_setup(tmp_path):
    """Stage a capabilities file that diverges from the committed
    generated YAMLs. The gate uses the real generated files via env
    vars, but here we override CAPABILITIES to a modified spec — that
    forces generator output to diverge from the committed files."""
    spec = yaml.safe_load(REAL_CAPABILITIES.read_text(encoding="utf-8"))
    # Bump a port number in services.redis — generator will emit different
    # NetworkPolicy bytes than the committed file.
    spec["services"]["redis"]["ports"] = [{"port": 6380, "protocol": "TCP"}]
    bad = tmp_path / "cap-drift.yaml"
    bad.write_text(yaml.safe_dump(spec))
    return bad


def test_generator_drift_blocks_deploy(drift_setup):
    """capabilities.yaml edited but generated files not regenerated → drift."""
    rc, _, _, report = _run_gate(
        "--quiet",
        env_overrides={"CAPABILITIES": str(drift_setup)},
    )
    assert rc == 1
    drift = next(c for c in report["checks"] if c["check"] == "generator_drift")
    assert drift["status"] == "FAIL"
    assert "regenerate" in drift["message"].lower() or "differs" in drift["message"].lower()


# ----------------------------------------------------------------- #
# 4. CLI behavior
# ----------------------------------------------------------------- #

def test_quiet_flag_suppresses_stdout():
    rc, out, _, _ = _run_gate("--quiet")
    # Quiet mode emits nothing on stdout from say(), only the json report.
    # (Tracebacks from failed sub-tools could still appear via tee.)
    assert "pre_deploy_check.sh" not in out  # banner suppressed


def test_unknown_arg_returns_error_exit_code():
    rc, _, err, _ = _run_gate("--this-flag-does-not-exist", "--quiet")
    assert rc == 2
    assert "unknown" in err.lower()


def test_help_flag_prints_usage_and_exits_zero():
    rc, out, _, _ = _run_gate("--help")
    assert rc == 0
    assert "pre_deploy_check" in out.lower()


# ----------------------------------------------------------------- #
# 5. JSON output schema
# ----------------------------------------------------------------- #

def test_json_report_is_valid_and_check_entries_well_formed():
    _, _, _, report = _run_gate("--quiet")
    for check in report["checks"]:
        for key in ("check", "status", "severity", "message"):
            assert key in check, f"finding missing {key}: {check}"
        assert check["status"] in {"PASS", "FAIL", "WARN", "SKIP"}
        assert check["severity"] in {"critical", "warning", "info"}


def test_verdict_matches_summary():
    """Internal consistency: if summary.critical > 0, verdict must be NO-GO."""
    _, _, _, report = _run_gate("--quiet")
    if report["summary"]["critical"] > 0:
        assert report["verdict"] == "NO-GO"
        assert report["exit_code"] == 1
    else:
        assert report["verdict"] == "GO"
        assert report["exit_code"] == 0


def test_report_file_env_var_respected(tmp_path):
    """REPORT_FILE env var routes the JSON output."""
    custom = tmp_path / "custom-report.json"
    _run_gate("--quiet", report_path=custom)
    assert custom.is_file(), "REPORT_FILE override was ignored"
    payload = json.loads(custom.read_text(encoding="utf-8"))
    assert "verdict" in payload
