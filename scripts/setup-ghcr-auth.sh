#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-synthetic-enterprise}"
SECRET_NAME="${SECRET_NAME:-ghcr-auth}"
REGISTRY="${REGISTRY:-ghcr.io}"
DEPLOYMENT="${DEPLOYMENT:-compliance-service}"
KUBECONFIG="${KUBECONFIG:-}"
DRY_RUN="${DRY_RUN:-false}"

if [[ -z "${KUBECONFIG}" ]]; then
  echo "ERROR: KUBECONFIG must point to the authoritative Talos kubeconfig." >&2
  exit 2
fi

if [[ -z "${GHCR_USERNAME:-}" || -z "${GHCR_TOKEN:-}" ]]; then
  echo "ERROR: GHCR_USERNAME and GHCR_TOKEN must be exported." >&2
  exit 2
fi

echo "Namespace: ${NAMESPACE}"
echo "Secret: ${SECRET_NAME}"
echo "Registry: ${REGISTRY}"
echo "Deployment: ${DEPLOYMENT}"
echo "Token: present (redacted)"

create_secret_cmd=(
  kubectl -n "${NAMESPACE}" create secret docker-registry "${SECRET_NAME}"
  "--docker-server=${REGISTRY}"
  "--docker-username=${GHCR_USERNAME}"
  "--docker-password=${GHCR_TOKEN}"
  "--dry-run=client"
  -o yaml
)

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "DRY RUN: would create/update imagePullSecret and patch deployment."
  "${create_secret_cmd[@]}" >/dev/null
  echo "DRY RUN: secret manifest renders successfully."
  echo "DRY RUN: kubectl -n ${NAMESPACE} patch deployment ${DEPLOYMENT} ..."
  exit 0
fi

"${create_secret_cmd[@]}" | kubectl apply -f -

kubectl -n "${NAMESPACE}" patch deployment "${DEPLOYMENT}" --type merge -p "{
  \"spec\": {
    \"template\": {
      \"spec\": {
        \"imagePullSecrets\": [
          {\"name\": \"${SECRET_NAME}\"}
        ]
      }
    }
  }
}"

kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT}" --timeout=180s
kubectl -n "${NAMESPACE}" get secret "${SECRET_NAME}"
kubectl -n "${NAMESPACE}" get deployment "${DEPLOYMENT}" -o jsonpath='{.spec.template.spec.imagePullSecrets}'
echo

