#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-synthetic-enterprise}"
DEPLOYMENT="${DEPLOYMENT:-compliance-service}"
KUBECONFIG="${KUBECONFIG:-}"
DRY_RUN="${DRY_RUN:-false}"

if [[ -z "${KUBECONFIG}" ]]; then
  echo "ERROR: KUBECONFIG must point to the authoritative Talos kubeconfig." >&2
  exit 2
fi

echo "Rollback target: ${NAMESPACE}/${DEPLOYMENT}"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "DRY RUN: would run kubectl rollout undo deployment/${DEPLOYMENT} -n ${NAMESPACE}"
  echo "DRY RUN: would wait for rollout status and list pods/endpoints."
  exit 0
fi

kubectl -n "${NAMESPACE}" rollout undo "deployment/${DEPLOYMENT}"
kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT}" --timeout=180s
kubectl -n "${NAMESPACE}" get deployment "${DEPLOYMENT}"
kubectl -n "${NAMESPACE}" get pods -l "app=${DEPLOYMENT}" -o wide
kubectl -n "${NAMESPACE}" get endpoints "${DEPLOYMENT}"

