#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${1:-}"
NAMESPACE="${NAMESPACE:-synthetic-enterprise}"
DEPLOYMENT="${DEPLOYMENT:-compliance-service}"
KUBECONFIG="${KUBECONFIG:-}"

if [[ -z "${RUN_ID}" ]]; then
  echo "Usage: $0 <run-id>" >&2
  exit 2
fi

if [[ -z "${KUBECONFIG}" ]]; then
  echo "ERROR: KUBECONFIG must point to the authoritative Talos kubeconfig." >&2
  exit 2
fi

timestamp="$(date -Is)"

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

capture() {
  local name="$1"
  shift
  set +e
  local output
  output="$("$@" 2>&1)"
  local status=$?
  set -e
  printf '"%s":{"status":%s,"output":%s}' "$name" "$status" "$(printf '%s' "$output" | json_escape)"
}

echo "{"
echo "\"run_id\":\"${RUN_ID}\","
echo "\"timestamp\":\"${timestamp}\","
echo "\"namespace\":\"${NAMESPACE}\","
echo "\"deployment\":\"${DEPLOYMENT}\","

capture context kubectl config current-context
echo ","
capture nodes kubectl get nodes -o wide
echo ","
capture deployments kubectl -n "${NAMESPACE}" get deployments
echo ","
capture pods kubectl -n "${NAMESPACE}" get pods -o wide
echo ","
capture services kubectl -n "${NAMESPACE}" get services
echo ","
capture endpoints kubectl -n "${NAMESPACE}" get endpoints
echo ","
capture events kubectl -n "${NAMESPACE}" get events --sort-by=.lastTimestamp
echo ","
capture rollout_history kubectl -n "${NAMESPACE}" rollout history "deployment/${DEPLOYMENT}"
echo ","
capture rollout_status kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT}" --timeout=60s
echo
echo "}"
