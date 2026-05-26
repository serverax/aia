#!/usr/bin/env bash
set -euo pipefail

echo "=== Dry-Run Deployment Verification ==="

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl not found on PATH" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MANIFESTS=(
  "${ROOT_DIR}/infrastructure/k3s/namespace.yaml"
  "${ROOT_DIR}/infrastructure/k3s/rbac-per-agent.yaml"
  "${ROOT_DIR}/infrastructure/k3s/network-policies-per-agent.yaml"
  "${ROOT_DIR}/infrastructure/compliance/compliance-service-deployment.yaml"
  "${ROOT_DIR}/infrastructure/compliance/compliance-service-svc.yaml"
  "${ROOT_DIR}/infrastructure/compliance/blue-green-traffic-split.yaml"
)

ok=0
skip=0
for manifest in "${MANIFESTS[@]}"; do
  if [[ ! -f "${manifest}" ]]; then
    echo "SKIP: missing ${manifest}"
    skip=$((skip + 1))
    continue
  fi
  echo "Checking: ${manifest}"
  kubectl apply --dry-run=client -f "${manifest}" >/dev/null
  ok=$((ok + 1))
done

echo "PASS: ${ok} manifest(s) validated; ${skip} missing/skipped"
