#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-ordinox-ai}"
DEPLOYMENT="${DEPLOYMENT:-compliance-service}"
TIMEOUT="${TIMEOUT:-120s}"
EVIDENCE_DIR="${EVIDENCE_DIR:-reports/blue-green}"
KUBECTL="${KUBECTL:-kubectl}"

mkdir -p "$EVIDENCE_DIR"

echo "=== rollout gate: context ==="
"$KUBECTL" config current-context | tee "$EVIDENCE_DIR/rollout-context.txt"

echo "=== rollout gate: deployment ==="
"$KUBECTL" -n "$NAMESPACE" rollout status "deployment/$DEPLOYMENT" "--timeout=$TIMEOUT" \
  | tee "$EVIDENCE_DIR/rollout-status.txt"

echo "=== rollout gate: resources ==="
"$KUBECTL" -n "$NAMESPACE" get deploy,pods,svc,endpoints,ingress -o wide \
  | tee "$EVIDENCE_DIR/rollout-resources.txt"

echo "=== rollout gate: blocked pod states ==="
if "$KUBECTL" -n "$NAMESPACE" get pods -o wide | grep -E 'CrashLoopBackOff|ImagePullBackOff|ErrImagePull|CreateContainerError'; then
  echo "ROLL_OUT_GATE=NO_GO blocked pod state detected"
  exit 1
fi

echo "=== rollout gate: base endpoint ==="
"$KUBECTL" -n "$NAMESPACE" get endpoints "$DEPLOYMENT" -o jsonpath='{.subsets[*].addresses[*].ip}' \
  | tee "$EVIDENCE_DIR/base-endpoints.txt"
echo

if ! test -s "$EVIDENCE_DIR/base-endpoints.txt"; then
  echo "ROLL_OUT_GATE=NO_GO base service has no endpoints"
  exit 1
fi

echo "ROLL_OUT_GATE=GO"
