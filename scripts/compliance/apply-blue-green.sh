#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-ordinox-ai}"
MANIFEST="${MANIFEST:-infrastructure/compliance/blue-green-traffic-split.yaml}"
EVIDENCE_DIR="${EVIDENCE_DIR:-reports/blue-green}"
KUBECTL="${KUBECTL:-kubectl}"

mkdir -p "$EVIDENCE_DIR"

echo "=== apply blue-green: context ==="
"$KUBECTL" config current-context | tee "$EVIDENCE_DIR/apply-context.txt"

echo "=== apply blue-green: server dry-run ==="
"$KUBECTL" apply --dry-run=server -f "$MANIFEST" | tee "$EVIDENCE_DIR/apply-dry-run.txt"

echo "=== apply blue-green: apply ==="
"$KUBECTL" apply -f "$MANIFEST" | tee "$EVIDENCE_DIR/apply-output.txt"

echo "=== apply blue-green: services ==="
"$KUBECTL" -n "$NAMESPACE" get svc compliance-service-blue compliance-service-green -o wide \
  | tee "$EVIDENCE_DIR/apply-services.txt"

echo "=== apply blue-green: ingresses ==="
"$KUBECTL" -n "$NAMESPACE" get ingress compliance-service-blue compliance-service-green-canary -o wide \
  | tee "$EVIDENCE_DIR/apply-ingresses.txt"

echo "=== apply blue-green: endpoints ==="
"$KUBECTL" -n "$NAMESPACE" get endpoints compliance-service-blue compliance-service-green -o wide \
  | tee "$EVIDENCE_DIR/apply-endpoints.txt"

echo "=== apply blue-green: canary weight ==="
WEIGHT="$("$KUBECTL" -n "$NAMESPACE" get ingress compliance-service-green-canary \
  -o jsonpath='{.metadata.annotations.nginx\.ingress\.kubernetes\.io/canary-weight}')"
echo "$WEIGHT" | tee "$EVIDENCE_DIR/canary-weight.txt"

if [ "$WEIGHT" != "5" ]; then
  echo "APPLY_BLUE_GREEN=FAIL expected canary weight 5, got $WEIGHT"
  exit 1
fi

echo "APPLY_BLUE_GREEN=PASS"
