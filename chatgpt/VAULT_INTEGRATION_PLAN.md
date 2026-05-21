# Vault Integration Plan

## Purpose

Sprint 8 DR validation needs a clear path from placeholder secrets to real Vault-backed secret recovery and audit-chain evidence.

## Current State

- Vault is not deployed in the target environment.
- `llm-api-keys` currently uses a placeholder Kubernetes Secret.
- Full audit-chain DR cannot pass until durable audit storage and Vault-backed secret recovery are available.

## Required Real Vault Capabilities

- Vault initialized and unsealed.
- Kubernetes auth enabled for `synthetic-enterprise`.
- Secret path for `ANTHROPIC_API_KEY`.
- Policy granting read access only to the compliance service account.
- Audit logging enabled for secret reads.
- DR restore procedure for Vault data or an approved external backup.

## Expected Secret Path

```text
secret/data/synthetic-enterprise/llm-api-keys
```

Expected key:

```text
ANTHROPIC_API_KEY
```

## Integration Verification

```bash
export KUBECONFIG=<talos-kubeconfig>

kubectl -n vault exec vault-0 -- vault status
kubectl -n vault exec vault-0 -- vault secrets list
kubectl -n vault exec vault-0 -- vault kv get secret/synthetic-enterprise/llm-api-keys
```

Do not print full secret values in logs.

## Mock Mode For DR Tests

Until Vault is available, use:

```bash
scripts/mock-vault-for-dr-test.sh status
scripts/mock-vault-for-dr-test.sh read-secret
scripts/mock-vault-for-dr-test.sh audit-check
```

Mock mode can validate DR script flow, but it cannot satisfy production DR sign-off.

## Gemini Dependency

Gemini/backend deployment must provide:

- whether it reads API keys directly from Kubernetes Secrets or Vault
- required Vault auth role/policy names
- expected secret paths
- health endpoint showing secret-provider readiness without leaking values

## Sprint 8 Acceptance Note

Vault absence is a documented limitation. It is acceptable for mock DR rehearsal only. Production DR sign-off requires real Vault deployment and restore evidence.

