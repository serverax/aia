# Worker Migration Plan — existing dev workers → Helm-managed agents

**Goal:** make the `synthetic-enterprise` Helm release the **canonical** AIA agent
deployment in `aia-dev`, replacing the pre-existing `aia-orchestrator-dev-worker`
and `aia-rag-dev-worker` (and any sibling dev workers) **without** running two
sets of consumers against the same Redis streams.

All commands run from a terminal with the **correct Talos/OrdinoxAI** kubeconfig
(never `aks-iterlaw-we-prod`). The chart deploys its **own** `se-redis`, so the
new agents do not share a stream backend with the old workers — but we still
cut over cleanly to avoid two "live" orchestrators and to keep one source of truth.

## 0. Inventory first (read-only)
Capture what the existing workers actually are before changing anything:
```bash
kubectl get deploy,po -n aia-dev -l '!app.kubernetes.io/managed-by'   # non-Helm objects
kubectl get deploy aia-orchestrator-dev-worker aia-rag-dev-worker -n aia-dev -o yaml > /tmp/old-workers.yaml
kubectl describe deploy aia-orchestrator-dev-worker -n aia-dev | sed -n '/Environment/,/Mounts/p'
kubectl describe deploy aia-rag-dev-worker          -n aia-dev | sed -n '/Environment/,/Mounts/p'
```
Note for each: image/tag, the `REDIS_HOST`/stream names they consume, and whether
they're currently **Ready** (if there's no Redis in `aia-dev`, they may already be
crash-looping — confirm). Keep `/tmp/old-workers.yaml` as the rollback artifact.

## 1. Quiesce the old workers (reversible)
Scale to zero rather than delete, so rollback is instant:
```bash
kubectl scale deploy aia-orchestrator-dev-worker --replicas=0 -n aia-dev
kubectl scale deploy aia-rag-dev-worker          --replicas=0 -n aia-dev
kubectl get deploy -n aia-dev    # confirm 0/0
```

## 2. Deploy the Helm release
Prereqs: `aia-secrets` exists; images `ghcr.io/serverax/<svc>:v0.1.0` pushed;
backend values confirmed.
```bash
helm upgrade --install synthetic-enterprise helm/synthetic-enterprise -n aia-dev \
  --set config.postgresUser=<role> --set config.postgresDb=<db>
# (Redis/Qdrant are created by the chart; postgresHost/Ollama already in values.)
kubectl rollout status deploy/synthetic-enterprise-orchestrator -n aia-dev --timeout=180s
```

## 3. Verify the new agents are canonical and healthy
```bash
kubectl get pods -n aia-dev -l app.kubernetes.io/part-of=synthetic-enterprise
kubectl exec deploy/synthetic-enterprise-orchestrator -n aia-dev -- env | grep -E 'REDIS_HOST|COMPLIANCE_SERVICE_URL|LLM_PROVIDER'
# REDIS_HOST must be se-redis... (NOT sakinaai-redis / Sakina), gate URL set.
```
Confirm only the `se-*` agents are consuming streams (the old ones are at 0).

## 4. Decommission the old workers (after a validation window)
Once the `se-*` agents are healthy and observed working:
```bash
kubectl delete deploy aia-orchestrator-dev-worker aia-rag-dev-worker -n aia-dev
# (any old ConfigMaps/Services for them too, once confirmed unused)
```

## Rollback
At any point before step 4:
```bash
helm uninstall synthetic-enterprise -n aia-dev          # remove new release
kubectl scale deploy aia-orchestrator-dev-worker --replicas=1 -n aia-dev
kubectl scale deploy aia-rag-dev-worker          --replicas=1 -n aia-dev
# or: kubectl apply -f /tmp/old-workers.yaml
```

## Open questions to resolve during inventory
- What Redis did the old workers use? There is **no Redis in `aia-dev`** today, so
  either they were misconfigured, idle, or pointing at an external instance —
  confirm so we don't lose in-flight work at cutover.
- Are there other non-Helm AIA workers besides these two? Step 0's label query
  should surface them.
- `aia-dev-web` and `aia-ollama-dev-cpu` are **left as-is** — the chart does not
  manage the web frontend or Ollama; only the agent workers are migrated.
