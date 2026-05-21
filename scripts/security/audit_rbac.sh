#!/usr/bin/env bash
# Thin wrapper around audit_rbac.py.
#
#   bash scripts/security/audit_rbac.sh           # live cluster, current KUBECONFIG
#   bash scripts/security/audit_rbac.sh /tmp/state.json   # offline from a JSON dump
#
# Exit codes propagate from the Python script:
#   0  RBAC matches capabilities.yaml
#   1  drift detected
#   2  invocation error
#
# CI usage: run nightly + on every capabilities.yaml change. Non-zero exit
# pages ops.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

if [[ $# -ge 1 ]]; then
    python -m scripts.security.audit_rbac --from-json "$1" "${@:2}"
else
    python -m scripts.security.audit_rbac
fi
