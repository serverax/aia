#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-status}"

case "${MODE}" in
  status)
    cat <<'JSON'
{
  "initialized": true,
  "sealed": false,
  "standby": false,
  "version": "mock-vault-sprint8",
  "cluster_name": "mock-dr-validation"
}
JSON
    ;;
  read-secret)
    cat <<'JSON'
{
  "path": "secret/data/synthetic-enterprise/llm-api-keys",
  "data": {
    "ANTHROPIC_API_KEY": "REDACTED"
  },
  "metadata": {
    "version": 1,
    "created_time": "mock"
  }
}
JSON
    ;;
  audit-check)
    cat <<'JSON'
{
  "audit_chain_valid": true,
  "latest_restored_event_age_minutes": 0,
  "source": "mock-vault-for-dr-test"
}
JSON
    ;;
  *)
    echo "Usage: $0 [status|read-secret|audit-check]" >&2
    exit 2
    ;;
esac

