#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-ordinox-ai}"
EVIDENCE_DIR="${EVIDENCE_DIR:-reports/blue-green}"
KUBECTL="${KUBECTL:-kubectl}"
DRY_RUN="${DRY_RUN:-false}"

mkdir -p "$EVIDENCE_DIR"

commands=(
  "$KUBECTL -n $NAMESPACE annotate ingress compliance-service-green-canary nginx.ingress.kubernetes.io/canary-weight=0 --overwrite"
  "$KUBECTL -n $NAMESPACE rollout undo deployment/compliance-service-green"
  "$KUBECTL -n $NAMESPACE get endpoints compliance-service-blue compliance-service-green -o wide"
)

echo "=== rollback blue-green ===" | tee "$EVIDENCE_DIR/rollback-output.txt"
for command in "${commands[@]}"; do
  echo "$command" | tee -a "$EVIDENCE_DIR/rollback-output.txt"
  if [ "$DRY_RUN" = "true" ]; then
    continue
  fi
  eval "$command" | tee -a "$EVIDENCE_DIR/rollback-output.txt"
done

if [ "$DRY_RUN" = "true" ]; then
  echo "ROLLBACK_BLUE_GREEN=DRY_RUN"
else
  WEIGHT="$("$KUBECTL" -n "$NAMESPACE" get ingress compliance-service-green-canary \
    -o jsonpath='{.metadata.annotations.nginx\.ingress\.kubernetes\.io/canary-weight}')"
  echo "canary-weight=$WEIGHT" | tee -a "$EVIDENCE_DIR/rollback-output.txt"
  if [ "$WEIGHT" != "0" ]; then
    echo "ROLLBACK_BLUE_GREEN=FAIL"
    exit 1
  fi
  echo "ROLLBACK_BLUE_GREEN=PASS"
fi
