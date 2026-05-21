#!/usr/bin/env bash
# Talos infrastructure triage — ops runs this on a machine that SHOULD be
# able to reach the production Talos node. Outputs a one-screen report
# that maps directly onto NEXT_ACTION_DECISION_TREE.md.
#
# Usage:
#   bash ops/talos-triage.sh                        # uses defaults below
#   TALOS_IP=1.2.3.4 bash ops/talos-triage.sh       # override target
#
# Tuning (env vars):
#   TALOS_IP          default: 148.251.247.56
#   TALOS_API_PORT    default: 50000   (Talos API — NOT 22 / NOT 6443)
#   HETZNER_SERVER_ID default: unset   (hcloud lookup skipped if unset)
#   REPORT_FILE       default: talos-triage-report.txt
#
# The script does NOT mutate anything. Safe to re-run. Safe to attach the
# report to a Slack/email reply.

set -uo pipefail
# Note: NOT set -e — we want to keep collecting evidence even if some
# probes fail. Each check sets a per-result flag instead.

TALOS_IP="${TALOS_IP:-148.251.247.56}"
TALOS_API_PORT="${TALOS_API_PORT:-50000}"
HETZNER_SERVER_ID="${HETZNER_SERVER_ID:-}"
REPORT_FILE="${REPORT_FILE:-talos-triage-report.txt}"

# Mirror all output to both stdout and the report file.
exec > >(tee "${REPORT_FILE}") 2>&1

API_REACHABLE="UNKNOWN"
TALOSCONFIG_PATH=""
TALOSCONFIG_EXISTS="NO"
TALOSCTL_INSTALLED="NO"
TALOSCTL_WORKS="UNKNOWN"
HETZNER_STATUS="UNKNOWN"

echo "==============================================================="
echo "  TALOS INFRASTRUCTURE TRIAGE REPORT"
echo "  Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "  Target:    ${TALOS_IP}:${TALOS_API_PORT}"
echo "  Host:      $(hostname)"
echo "==============================================================="
echo

# ---------------------------------------------------------------- #
# 1. TCP probe — is the Talos API even reachable from this network?
# ---------------------------------------------------------------- #
echo "[1/4] TCP probe of Talos API endpoint"
if timeout 5 bash -c "exec 3<>/dev/tcp/${TALOS_IP}/${TALOS_API_PORT}" 2>/dev/null; then
    echo "      OK    : ${TALOS_IP}:${TALOS_API_PORT} accepts TCP connections"
    API_REACHABLE="YES"
else
    echo "      FAIL  : cannot open TCP to ${TALOS_IP}:${TALOS_API_PORT}"
    echo "              (Hetzner firewall blocking port ${TALOS_API_PORT}, or node down)"
    API_REACHABLE="NO"
fi
echo

# ---------------------------------------------------------------- #
# 2. Discover any talosconfig already on this filesystem
# ---------------------------------------------------------------- #
echo "[2/4] Looking for existing talosconfig"

CANDIDATES=()
[[ -f "${HOME}/.talos/config" ]] && CANDIDATES+=("${HOME}/.talos/config")
[[ -f "./talosconfig"          ]] && CANDIDATES+=("./talosconfig")
[[ -f "./talos/talosconfig"    ]] && CANDIDATES+=("./talos/talosconfig")
[[ -n "${TALOSCONFIG:-}"       ]] && [[ -f "${TALOSCONFIG}" ]] && CANDIDATES+=("${TALOSCONFIG}")

# Bounded search for anything else named "talosconfig" — depth limited so
# this doesn't scan a 500GB $HOME.
while IFS= read -r line; do
    CANDIDATES+=("${line}")
done < <(find "${HOME}" -maxdepth 4 -name "talosconfig" -o -name "config" \
            -path "*/.talos/*" 2>/dev/null | head -10)

# Deduplicate.
mapfile -t CANDIDATES < <(printf '%s\n' "${CANDIDATES[@]}" | awk 'NF' | sort -u)

if [[ "${#CANDIDATES[@]}" -gt 0 ]]; then
    echo "      OK    : found ${#CANDIDATES[@]} candidate(s):"
    for path in "${CANDIDATES[@]}"; do
        echo "                ${path}"
    done
    TALOSCONFIG_PATH="${CANDIDATES[0]}"
    TALOSCONFIG_EXISTS="YES"
    echo "      using ${TALOSCONFIG_PATH} for subsequent checks"
else
    echo "      FAIL  : no talosconfig found under \$HOME, ./, ./talos/, or \$TALOSCONFIG"
fi
echo

# ---------------------------------------------------------------- #
# 3. talosctl install + functional check
# ---------------------------------------------------------------- #
echo "[3/4] talosctl health check"

if command -v talosctl >/dev/null 2>&1; then
    TALOSCTL_INSTALLED="YES"
    echo "      OK    : talosctl installed ($(talosctl version --client --short 2>/dev/null | head -1))"

    if [[ "${TALOSCONFIG_EXISTS}" == "YES" ]]; then
        # Two checks: (1) config parses; (2) we can hit a node with it.
        if talosctl --talosconfig "${TALOSCONFIG_PATH}" config info >/dev/null 2>&1; then
            echo "      OK    : config parses cleanly"
            if timeout 10 talosctl --talosconfig "${TALOSCONFIG_PATH}" \
                    --nodes "${TALOS_IP}" version --short >/dev/null 2>&1; then
                echo "      OK    : talosctl can reach ${TALOS_IP}"
                TALOSCTL_WORKS="YES"
            else
                echo "      FAIL  : talosctl cannot reach ${TALOS_IP} with this config"
                echo "              (cert/CA mismatch, wrong endpoint, or network block)"
                TALOSCTL_WORKS="NO"
            fi
        else
            echo "      FAIL  : config does not parse"
            TALOSCTL_WORKS="NO"
        fi
    else
        echo "      SKIP  : no talosconfig found, cannot test connectivity"
    fi
else
    echo "      FAIL  : talosctl not installed"
    echo "              Install: https://www.talos.dev/latest/talos-guides/install/talosctl/"
fi
echo

# ---------------------------------------------------------------- #
# 4. Hetzner server state (skipped if HETZNER_SERVER_ID unset)
# ---------------------------------------------------------------- #
echo "[4/4] Hetzner server state"
if [[ -z "${HETZNER_SERVER_ID}" ]]; then
    echo "      SKIP  : HETZNER_SERVER_ID not set"
    echo "              Re-run with HETZNER_SERVER_ID=<id> hcloud token configured"
elif ! command -v hcloud >/dev/null 2>&1; then
    echo "      SKIP  : hcloud CLI not installed (skipping Hetzner check)"
else
    HETZNER_STATUS=$(hcloud server describe "${HETZNER_SERVER_ID}" -o json 2>/dev/null \
        | jq -r '.server.status // "UNREACHABLE"' 2>/dev/null || echo "UNREACHABLE")
    echo "      ${HETZNER_STATUS}: hcloud reports server ${HETZNER_SERVER_ID} = ${HETZNER_STATUS}"
fi
echo

# ---------------------------------------------------------------- #
# Summary block — designed for the decision tree.
# ---------------------------------------------------------------- #
echo "==============================================================="
echo "  SUMMARY  (paste this block into the deployment-team reply)"
echo "==============================================================="
echo "  API_REACHABLE     = ${API_REACHABLE}"
echo "  TALOSCONFIG       = ${TALOSCONFIG_EXISTS}${TALOSCONFIG_PATH:+ (${TALOSCONFIG_PATH})}"
echo "  TALOSCTL_INSTALLED= ${TALOSCTL_INSTALLED}"
echo "  TALOSCTL_WORKS    = ${TALOSCTL_WORKS}"
echo "  HETZNER_STATUS    = ${HETZNER_STATUS}"
echo

if   [[ "${API_REACHABLE}" == "YES" && "${TALOSCTL_WORKS}" == "YES" ]]; then
    echo "  VERDICT: PRODUCTION READY"
    echo "  -> Option A in NEXT_ACTION_DECISION_TREE.md"
    echo "     Attach ${TALOSCONFIG_PATH} + CA cert to deployment-team reply."
elif [[ "${API_REACHABLE}" == "YES" && "${TALOSCONFIG_EXISTS}" == "NO" ]]; then
    echo "  VERDICT: NEEDS CONFIG"
    echo "  -> Option B in NEXT_ACTION_DECISION_TREE.md"
    echo "     Run 'talosctl gen config' or fetch from the original installer."
elif [[ "${API_REACHABLE}" == "NO" ]]; then
    echo "  VERDICT: NETWORK BLOCKED"
    echo "  -> Option C in NEXT_ACTION_DECISION_TREE.md"
    echo "     Open Hetzner firewall TCP/${TALOS_API_PORT} from ops network, re-run script."
else
    echo "  VERDICT: INCONCLUSIVE"
    echo "  -> Option D in NEXT_ACTION_DECISION_TREE.md"
    echo "     Re-run with bash -x for verbose; attach full report and escalate."
fi
echo
echo "  Full report saved to: ${REPORT_FILE}"
echo "==============================================================="
