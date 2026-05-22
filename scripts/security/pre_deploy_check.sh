#!/usr/bin/env bash
# pre_deploy_check.sh — Sprint 9 deployment safety gate.
#
# Runs four checks before any kubectl apply / Flux reconcile:
#
#   1. CAPABILITY VALIDATOR  — capabilities.yaml semantic correctness
#                              (undefined service refs, bad k8s names,
#                              empty selectors, etc.)
#   2. GENERATOR DRIFT       — regenerates per-agent policies into a temp
#                              dir, diffs against committed files. Drift
#                              means "someone edited capabilities.yaml
#                              but forgot to regenerate" — the live cluster
#                              will be stale.
#   3. POLICY RUNTIME TESTS  — simulator-based unit tests proving the
#                              generated NetworkPolicies actually permit
#                              what capabilities.yaml says they should
#                              and deny everything else.
#   4. MANIFEST DRY-RUN      — kubectl apply --dry-run=client on every
#                              .yaml in infrastructure/k3s/. Catches
#                              gross schema errors.
#
# Plus optional --live mode:
#   5. RBAC AUDIT            — scripts/security/audit_rbac.py against the
#                              live cluster. Drift = somebody hand-edited
#                              RBAC or a Flux reconcile failed.
#
# Exit codes:
#   0  GO       — safe to deploy. May have warnings/info findings.
#   1  NO-GO    — at least one CRITICAL finding. Do not deploy.
#   2  ERROR    — script itself failed (missing dep, broken file, etc.)
#
# Output:
#   stdout    — human-readable report
#   $REPORT_FILE (default /tmp/pre_deploy_check.json) — JSON for CI
#
# Usage examples:
#   bash scripts/security/pre_deploy_check.sh
#   bash scripts/security/pre_deploy_check.sh --live
#   bash scripts/security/pre_deploy_check.sh --live --from-json /tmp/state.json
#   REPORT_FILE=/dev/null bash scripts/security/pre_deploy_check.sh --quiet
#
# CI integration (GitHub Actions):
#   - name: Pre-deploy safety gate
#     run: |
#       bash scripts/security/pre_deploy_check.sh
#       # Exit-1 from this step fails the job.

set -uo pipefail
# NOT set -e: we want to keep running checks even if one fails, and
# aggregate all findings before exiting.

# ---------------------------------------------------------------- #
# Config
# ---------------------------------------------------------------- #

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

CAPABILITIES="${CAPABILITIES:-infrastructure/security/capabilities.yaml}"
MANIFEST_DIR="${MANIFEST_DIR:-infrastructure/k3s}"
NETWORK_POLICIES_FILE="${NETWORK_POLICIES_FILE:-infrastructure/k3s/network-policies-per-agent.yaml}"
RBAC_FILE="${RBAC_FILE:-infrastructure/k3s/rbac-per-agent.yaml}"
REPORT_FILE="${REPORT_FILE:-/tmp/pre_deploy_check.json}"

# Find a real Python. On Windows the bare `python` command often resolves
# to the Microsoft Store shim (which prints "Python was not found" and
# exits non-zero), so `command -v` isn't enough — we have to actually
# invoke each candidate and check the exit code.
_find_python() {
    local cand
    for cand in "${PYTHON:-}" python3 python py; do
        [[ -z "${cand}" ]] && continue
        if "${cand}" -c "import sys; sys.exit(0)" >/dev/null 2>&1; then
            echo "${cand}"
            return 0
        fi
    done
    return 1
}
PYTHON="$(_find_python || true)"
if [[ -z "${PYTHON}" ]]; then
    echo "ERROR: no working Python interpreter found (tried python3, python, py)" >&2
    echo "       set PYTHON=/path/to/python and re-run" >&2
    exit 2
fi

MODE="offline"
RBAC_FROM_JSON=""
QUIET="${QUIET:-0}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --live)        MODE="live"; shift ;;
        --from-json)   RBAC_FROM_JSON="$2"; MODE="live"; shift 2 ;;
        --quiet)       QUIET=1; shift ;;
        -h|--help)
            sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "ERROR: unknown arg: $1" >&2
            exit 2
            ;;
    esac
done

# ---------------------------------------------------------------- #
# Output helpers
# ---------------------------------------------------------------- #

# Findings accumulator: each entry is one JSON object per line.
FINDINGS_TMP="$(mktemp)"
trap 'rm -f "${FINDINGS_TMP}"' EXIT

CRITICAL=0
WARNING=0
INFO=0

# Args: check_name, status (PASS|FAIL|WARN|SKIP), severity, message
record() {
    local check="$1" status="$2" severity="$3" message="$4"
    case "${severity}" in
        critical) CRITICAL=$((CRITICAL+1));;
        warning)  WARNING=$((WARNING+1));;
        info)     INFO=$((INFO+1));;
    esac
    ${PYTHON} -c "
import json, sys
print(json.dumps({
    'check':    sys.argv[1],
    'status':   sys.argv[2],
    'severity': sys.argv[3],
    'message':  sys.argv[4],
}))
" "${check}" "${status}" "${severity}" "${message}" >> "${FINDINGS_TMP}"
}

say() {
    [[ "${QUIET}" == "1" ]] && return 0
    echo "$@"
}

heading() {
    [[ "${QUIET}" == "1" ]] && return 0
    echo
    echo "── $1 ──"
}

# ---------------------------------------------------------------- #
# Check 1 — capability validator
# ---------------------------------------------------------------- #

check_capability_validator() {
    heading "1/5 capability validator"
    if [[ ! -f "${CAPABILITIES}" ]]; then
        record "capability_validator" "FAIL" "critical" \
            "capabilities.yaml not found at ${CAPABILITIES}"
        say "  FAIL: ${CAPABILITIES} not found"
        return 1
    fi

    local tmp; tmp="$(mktemp)"
    if ! ${PYTHON} -m scripts.security.capability_validator "${CAPABILITIES}" --json > "${tmp}" 2>&1; then
        # validator exits 1 on critical findings; we want to surface them, not exit.
        :
    fi

    # Parse JSON output and propagate every finding.
    local n_crit n_warn n_info
    n_crit=$(${PYTHON} -c "import json,sys; print(json.load(open(sys.argv[1]))['summary']['critical'])" "${tmp}" 2>/dev/null || echo 0)
    n_warn=$(${PYTHON} -c "import json,sys; print(json.load(open(sys.argv[1]))['summary']['warning'])" "${tmp}" 2>/dev/null || echo 0)
    n_info=$(${PYTHON} -c "import json,sys; print(json.load(open(sys.argv[1]))['summary']['info'])" "${tmp}" 2>/dev/null || echo 0)

    if [[ "${n_crit}" -gt 0 ]]; then
        # Dump the full text report for the operator's benefit.
        ${PYTHON} -m scripts.security.capability_validator "${CAPABILITIES}" 2>&1 \
            | sed 's/^/  /' | tee -a /dev/stderr >/dev/null || true
        record "capability_validator" "FAIL" "critical" \
            "${n_crit} critical findings (see report)"
        say "  FAIL: ${n_crit} critical, ${n_warn} warning, ${n_info} info"
    elif [[ "${n_warn}" -gt 0 ]]; then
        record "capability_validator" "WARN" "warning" \
            "${n_warn} warning(s); see capability_validator --json output"
        say "  WARN: ${n_warn} warning, ${n_info} info"
    else
        record "capability_validator" "PASS" "info" "all semantic checks passed"
        say "  PASS"
    fi
    rm -f "${tmp}"
}

# ---------------------------------------------------------------- #
# Check 2 — generator drift
# ---------------------------------------------------------------- #

check_generator_drift() {
    heading "2/5 generator drift"
    if [[ ! -f "${NETWORK_POLICIES_FILE}" || ! -f "${RBAC_FILE}" ]]; then
        record "generator_drift" "FAIL" "critical" \
            "expected generator outputs missing — run generate_policies.py"
        say "  FAIL: generator outputs missing"
        return 1
    fi

    local tmpdir; tmpdir="$(mktemp -d)"
    local tmp_np="${tmpdir}/np.yaml"
    local tmp_rbac="${tmpdir}/rbac.yaml"

    if ! ${PYTHON} -m scripts.security.generate_policies \
            --in "${CAPABILITIES}" \
            --network-out "${tmp_np}" \
            --rbac-out "${tmp_rbac}" >/dev/null 2>&1; then
        record "generator_drift" "FAIL" "critical" "generator crashed"
        say "  FAIL: generator could not run"
        rm -rf "${tmpdir}"
        return 1
    fi

    local np_diff rbac_diff
    np_diff="$(diff -q "${tmp_np}" "${NETWORK_POLICIES_FILE}" 2>&1 || true)"
    rbac_diff="$(diff -q "${tmp_rbac}" "${RBAC_FILE}" 2>&1 || true)"

    if [[ -n "${np_diff}" || -n "${rbac_diff}" ]]; then
        record "generator_drift" "FAIL" "critical" \
            "generator output differs from committed files — regenerate + commit"
        say "  FAIL: drift detected. Run:"
        say "     python scripts/security/generate_policies.py"
        say "     git diff infrastructure/k3s/{network-policies,rbac}-per-agent.yaml"
    else
        record "generator_drift" "PASS" "info" \
            "committed generator outputs match capabilities.yaml"
        say "  PASS"
    fi
    rm -rf "${tmpdir}"
}

# ---------------------------------------------------------------- #
# Check 3 — policy runtime tests
# ---------------------------------------------------------------- #

check_policy_runtime() {
    heading "3/5 policy runtime tests"
    local out; out="$(mktemp)"

    if ${PYTHON} -m pytest tests/security/test_policies_runtime.py \
            -m unit --no-header -q --tb=no > "${out}" 2>&1; then
        local n_pass
        n_pass="$(grep -oE '[0-9]+ passed' "${out}" | head -1 || echo '?')"
        record "policy_runtime_tests" "PASS" "info" \
            "${n_pass}; agents reach what capabilities.yaml says"
        say "  PASS: ${n_pass}"
    else
        local n_fail
        n_fail="$(grep -oE '[0-9]+ failed' "${out}" | head -1 || echo 'failures')"
        record "policy_runtime_tests" "FAIL" "critical" \
            "${n_fail} in policy simulator — generated policies do NOT match capabilities.yaml intent"
        say "  FAIL: ${n_fail}"
        tail -20 "${out}" | sed 's/^/    /' | tee -a /dev/stderr >/dev/null
    fi
    rm -f "${out}"
}

# ---------------------------------------------------------------- #
# Check 4 — manifest client-side dry-run
# ---------------------------------------------------------------- #

check_manifest_dry_run() {
    heading "4/5 manifest dry-run (client-side)"
    if ! command -v kubectl >/dev/null 2>&1; then
        record "manifest_dry_run" "SKIP" "warning" "kubectl not on PATH"
        say "  SKIP: kubectl not installed"
        return 0
    fi

    local ok=0 fail=0 crd_skip=0
    while IFS= read -r -d '' f; do
        local out
        out="$(kubectl apply --dry-run=client -f "$f" 2>&1)"
        local rc=$?
        if [[ "${rc}" -eq 0 ]]; then
            ok=$((ok+1))
        elif echo "${out}" | grep -q "no matches for kind"; then
            # CRD-dependent resource (sigstore ClusterImagePolicy, Kyverno
            # ClusterPolicy). Can only validate server-side post-CRD install.
            crd_skip=$((crd_skip+1))
            say "  CRD-DEP (server-side validate): $f"
        else
            fail=$((fail+1))
            say "  FAIL: $f"
            echo "${out}" | sed 's/^/        /' | head -3
        fi
    done < <(find "${MANIFEST_DIR}" -maxdepth 2 -name '*.yaml' -print0)

    if [[ "${fail}" -gt 0 ]]; then
        record "manifest_dry_run" "FAIL" "critical" \
            "${fail} manifest(s) failed client-side dry-run"
    elif [[ "${crd_skip}" -gt 0 ]]; then
        record "manifest_dry_run" "WARN" "warning" \
            "${ok} ok, ${crd_skip} require server-side validation (CRD-dependent)"
        say "  PARTIAL: ${ok} ok, ${crd_skip} CRD-dependent (run server-side post-CRD install)"
    else
        record "manifest_dry_run" "PASS" "info" "${ok} manifests validate"
        say "  PASS: ${ok} manifests"
    fi
}

# ---------------------------------------------------------------- #
# Check 5 — RBAC audit (live mode only)
# ---------------------------------------------------------------- #

check_rbac_audit() {
    heading "5/5 RBAC audit"
    if [[ "${MODE}" != "live" ]]; then
        record "rbac_audit" "SKIP" "info" "offline mode; pass --live to enable"
        say "  SKIP: offline mode (use --live or --from-json)"
        return 0
    fi

    local args=()
    if [[ -n "${RBAC_FROM_JSON}" ]]; then
        args+=("--from-json" "${RBAC_FROM_JSON}")
    fi
    args+=("--capabilities" "${CAPABILITIES}" "--quiet")

    local out rc
    out="$(${PYTHON} -m scripts.security.audit_rbac "${args[@]}" 2>&1)"
    rc=$?

    if [[ "${rc}" -eq 0 ]]; then
        record "rbac_audit" "PASS" "info" "deployed RBAC matches capabilities.yaml"
        say "  PASS: no drift"
    elif [[ "${rc}" -eq 1 ]]; then
        # Audit returns 1 for any drift; we have to peek at the output to
        # tell critical (MISSING / MISMATCH) from warning (EXTRA).
        local n_err n_warn
        n_err="$(echo "${out}" | grep -c '^\[ERROR' || true)"
        n_warn="$(echo "${out}" | grep -c '^\[WARNING' || true)"
        if [[ "${n_err}" -gt 0 ]]; then
            record "rbac_audit" "FAIL" "critical" \
                "${n_err} error finding(s) — MISSING or MISMATCH RBAC objects"
            say "  FAIL: ${n_err} error(s), ${n_warn} warning(s)"
        else
            record "rbac_audit" "WARN" "warning" \
                "${n_warn} warning finding(s) — EXTRA RBAC objects not in capabilities.yaml"
            say "  WARN: ${n_warn} extra resource(s)"
        fi
        echo "${out}" | sed 's/^/    /' | tee -a /dev/stderr >/dev/null
    else
        record "rbac_audit" "FAIL" "critical" "audit script crashed (exit ${rc})"
        say "  FAIL: audit script exit ${rc}"
        echo "${out}" | sed 's/^/    /' | tee -a /dev/stderr >/dev/null
    fi
}

# ---------------------------------------------------------------- #
# Aggregate + emit
# ---------------------------------------------------------------- #

emit_json_report() {
    local verdict_arg="$1" exit_code_arg="$2"
    ${PYTHON} -m scripts.security._emit_report \
        "${FINDINGS_TMP}" "${REPORT_FILE}" \
        "${CRITICAL}" "${WARNING}" "${INFO}" \
        "${MODE}" "${verdict_arg}" "${exit_code_arg}"
}

main() {
    say "════════════════════════════════════════════════════════"
    say "  pre_deploy_check.sh — Sprint 9 safety gate"
    say "  mode=${MODE}  capabilities=${CAPABILITIES}"
    say "════════════════════════════════════════════════════════"

    check_capability_validator
    check_generator_drift
    check_policy_runtime
    check_manifest_dry_run
    check_rbac_audit

    say
    say "════════════════════════════════════════════════════════"
    say "  SUMMARY: ${CRITICAL} critical, ${WARNING} warning, ${INFO} info"

    local verdict exit_code
    if [[ "${CRITICAL}" -gt 0 ]]; then
        verdict="NO-GO"
        exit_code=1
        say "  VERDICT: NO-GO — do not deploy"
    else
        verdict="GO"
        exit_code=0
        say "  VERDICT: GO — safe to deploy"
        if [[ "${WARNING}" -gt 0 ]]; then
            say "  (${WARNING} warning(s) — review but non-blocking)"
        fi
    fi
    say "  JSON report: ${REPORT_FILE}"
    say "════════════════════════════════════════════════════════"

    emit_json_report "${verdict}" "${exit_code}"
    exit "${exit_code}"
}

main "$@"
