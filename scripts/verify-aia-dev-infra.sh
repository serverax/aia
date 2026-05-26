#!/usr/bin/env bash
set -euo pipefail

DEV_NS="aia-dev"
STORAGE_NS="aia-dev-storage"
MONITORING_NS="aia-dev-monitoring"
SECURITY_NS="aia-dev-security"
DEV_DOMAIN="dev.ordinoxai.com"

REPORT_DIR="/mnt/f/aia-dev/generated/evidence"
mkdir -p "${REPORT_DIR}"

REPORT="${REPORT_DIR}/aia-dev-infra-verification-$(date +%Y%m%d-%H%M%S).txt"

{
  echo "AIA DEV INFRA VERIFICATION"
  echo "Generated: $(date -Is)"
  echo "Dev namespace: ${DEV_NS}"
  echo "Storage namespace: ${STORAGE_NS}"
  echo "Dev domain: ${DEV_DOMAIN}"
  echo ""

  echo "=== kubectl context ==="
  kubectl config current-context || true
  echo ""

  echo "=== namespaces ==="
  kubectl get ns "${DEV_NS}" "${STORAGE_NS}" "${MONITORING_NS}" "${SECURITY_NS}" -o wide || true
  echo ""

  echo "=== dev pods ==="
  kubectl -n "${DEV_NS}" get pods -o wide || true
  echo ""

  echo "=== storage pods ==="
  kubectl -n "${STORAGE_NS}" get pods -o wide || true
  echo ""

  echo "=== services ==="
  kubectl -n "${DEV_NS}" get svc -o wide || true
  kubectl -n "${STORAGE_NS}" get svc -o wide || true
  echo ""

  echo "=== ingress ==="
  kubectl -n "${DEV_NS}" get ingress -o wide || true
  echo ""

  echo "=== rollout ==="
  kubectl -n "${DEV_NS}" rollout status deploy/aia-dev-web --timeout=60s || true
  kubectl -n "${DEV_NS}" rollout status deploy/aia-ollama-dev-cpu --timeout=60s || true
  kubectl -n "${DEV_NS}" rollout status deploy/aia-orchestrator-dev-worker --timeout=60s || true
  kubectl -n "${DEV_NS}" rollout status deploy/aia-rag-dev-worker --timeout=60s || true
  kubectl -n "${STORAGE_NS}" rollout status deploy/minio-dev --timeout=60s || true
  echo ""

  echo "=== DNS ==="
  if command -v dig >/dev/null 2>&1; then
    dig +short "${DEV_DOMAIN}" || true
  else
    echo "dig not installed"
  fi
  echo ""

  echo "=== HTTP check ==="
  if command -v curl >/dev/null 2>&1; then
    curl -Ik "https://${DEV_DOMAIN}" || true
  else
    echo "curl not installed"
  fi
  echo ""

  echo "=== DB file check ==="
  ls -la /mnt/f/aia-dev/generated/supabase/aia_dev_schema.sql || true
  echo ""

  echo "NOTE:"
  echo "This confirms generated files and Kubernetes runtime state."
  echo "DB is only confirmed after psql migration output is provided."
} | tee "${REPORT}"

echo ""
echo "Verification report saved:"
echo "${REPORT}"
