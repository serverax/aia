# Key Injection Procedure

## Purpose

This procedure defines how Sprint 8 injects runtime keys without committing secrets to Git or pasting them into logs.

## Required Inputs

- `ANTHROPIC_API_KEY`: provided by Ops or the approved secret manager.
- Optional `GHCR_USERNAME` and `GHCR_TOKEN`: required only when pulling private GHCR images.
- Authoritative Talos kubeconfig exported as `KUBECONFIG`.

## Safety Rules

- Never commit real keys.
- Never paste full keys into chat, logs, release notes, or test output.
- Only print whether a key is present and a short prefix when needed.
- Rotate placeholder keys before production release.

## Inject Anthropic API Key

Preferred runtime method:

```bash
export KUBECONFIG=<path-to-talos-kubeconfig>
export ANTHROPIC_API_KEY='<real-key-from-secret-manager>'

kubectl -n synthetic-enterprise create secret generic llm-api-keys \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Verification without leaking the key:

```bash
kubectl -n synthetic-enterprise get secret llm-api-keys
kubectl -n synthetic-enterprise get secret llm-api-keys \
  -o jsonpath='{.data.ANTHROPIC_API_KEY}' | base64 -d | head -c 8
echo ''
```

Expected:

```text
NAME           TYPE     DATA
llm-api-keys   Opaque   1
sk-...
```

## Rotate Anthropic API Key

```bash
export ANTHROPIC_API_KEY='<new-real-key>'

kubectl -n synthetic-enterprise create secret generic llm-api-keys \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n synthetic-enterprise rollout restart deployment/compliance-service
kubectl -n synthetic-enterprise rollout status deployment/compliance-service
```

## Placeholder Key Policy

Placeholder keys are allowed only for non-production wiring tests:

```bash
kubectl -n synthetic-enterprise create secret generic llm-api-keys \
  --from-literal=ANTHROPIC_API_KEY='placeholder-update-later' \
  --dry-run=client -o yaml | kubectl apply -f -
```

Any report using a placeholder key must state:

```text
API key state: placeholder, not production-valid.
```

## Failure Handling

| Failure | Meaning | Recovery |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` empty | key not exported | retrieve from Ops/secret manager |
| secret missing after apply | wrong namespace/context | verify `KUBECONFIG` and namespace |
| pod still using old key | deployment not restarted or app caches env | restart deployment |
| key printed in logs | credential exposure | rotate key immediately |

