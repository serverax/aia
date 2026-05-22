# Staging Deploy Runbook — Flux (GitOps)

This is the **Flux variant** of `docs/STAGING-DEPLOY-RUNBOOK.md`. Use this one when the target cluster has Flux controllers healthy (per ops, `admin@ordinox-talos-ha` does). Manifests are *not* applied via `kubectl apply`; they land in `clusters/ordinox-ai/` in the `serverax/aia` repo, Flux reconciles on its own.

The `kubectl apply` runbook is still valid for ad-hoc inspection or for clusters where Flux isn't running. Don't run them simultaneously against the same cluster — out-of-band edits will fight Flux's reconciliation loop.

---

## Mental model — what changes vs the kubectl runbook

| Step | kubectl runbook | Flux runbook |
|---|---|---|
| Apply a manifest | `kubectl apply -f <file>` | `git commit && git push`, wait for Flux |
| Verify rollout | `kubectl rollout status` | `flux get kustomization <name>` |
| Force re-apply | re-run `kubectl apply` | `flux reconcile kustomization <name>` |
| Rollback | `kubectl delete` + reapply old YAML | `git revert <sha> && git push`, OR `flux suspend kustomization <name>` |
| Out-of-band fix | `kubectl edit ...` | **DON'T** — Flux will revert; fix the YAML in git |

---

## Step 0 — Preflight (5 min)

```bash
export KUBECONFIG=~/.kube/aia-config.yaml      # talosctl-issued config

# Cluster + Flux health
kubectl config current-context                 # expect: admin@ordinox-talos-ha
kubectl get nodes -o wide                      # expect: 3 Ready
flux check                                     # all controllers healthy
flux get sources git                           # expect: a GitRepository pointing at serverax/aia, READY=True
flux get kustomizations -A                     # list what's already managed
```

✅ Gate: `flux check` reports all controllers healthy AND there's a `GitRepository` source on the `aia` repo.

If `flux check` fails or the GitRepository doesn't exist, **stop** — Flux bootstrap isn't complete; that's ops's prerequisite, not part of this runbook.

---

## Step 1 — Add the Flux directory structure for ordinox-ai (one-time)

The first deploy creates a directory in the repo that Flux will own. After this, every subsequent change is just a commit.

Create this in your local checkout, commit, push:

```
clusters/ordinox-ai/
├── infrastructure.yaml      # Kustomization → infrastructure/k3s + infrastructure/security
├── security-controllers.yaml  # HelmReleases for sigstore + Kyverno (CRD-providers; must reconcile first)
└── apps.yaml                # Kustomization → application deployments
```

### `clusters/ordinox-ai/security-controllers.yaml`

These install the CRDs that the security policies depend on. They must reconcile **before** the policy manifests, so they live in their own Kustomization.

```yaml
---
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: sigstore
  namespace: flux-system
spec:
  interval: 24h
  url: https://sigstore.github.io/helm-charts
---
apiVersion: source.toolkit.fluxcd.io/v1
kind: HelmRepository
metadata:
  name: kyverno
  namespace: flux-system
spec:
  interval: 24h
  url: https://kyverno.github.io/kyverno
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: policy-controller
  namespace: cosign-system
spec:
  interval: 1h
  install:
    createNamespace: true
  chart:
    spec:
      chart: policy-controller
      version: "0.10.x"
      sourceRef:
        kind: HelmRepository
        name: sigstore
        namespace: flux-system
---
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: kyverno
  namespace: kyverno
spec:
  interval: 1h
  install:
    createNamespace: true
  chart:
    spec:
      chart: kyverno
      version: "3.2.x"
      sourceRef:
        kind: HelmRepository
        name: kyverno
        namespace: flux-system
```

### `clusters/ordinox-ai/infrastructure.yaml`

```yaml
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: ordinox-ai-namespace
  namespace: flux-system
spec:
  interval: 10m
  sourceRef:
    kind: GitRepository
    name: aia
  path: ./infrastructure/k3s
  prune: true
  wait: true
  timeout: 5m
  # Only apply the namespace file in this Kustomization so it lands before everything else.
  patches:
    - target: { kind: "*" }
      patch: |
        # We use targetSelectors via include list below instead — clearer.
  # Simpler: split into a dedicated dir or list explicit resources via a kustomization.yaml.
  # See note below this snippet about the recommended layout.
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: ordinox-ai-data-layer
  namespace: flux-system
spec:
  interval: 10m
  dependsOn:
    - { name: ordinox-ai-namespace }
  sourceRef:
    kind: GitRepository
    name: aia
  path: ./infrastructure/k3s
  prune: true
  wait: true
  timeout: 10m
  healthChecks:
    - apiVersion: apps/v1
      kind: StatefulSet
      name: postgres
      namespace: ordinox-ai
    - apiVersion: apps/v1
      kind: StatefulSet
      name: redis
      namespace: ordinox-ai
    - apiVersion: apps/v1
      kind: Deployment
      name: jaeger
      namespace: ordinox-ai
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: ordinox-ai-security
  namespace: flux-system
spec:
  interval: 10m
  dependsOn:
    - { name: ordinox-ai-namespace }
  sourceRef:
    kind: GitRepository
    name: aia
  path: ./infrastructure/security
  prune: true
  wait: true
  timeout: 5m
```

> **Recommended cleanup before committing this:** the snippets above point three Kustomizations at the same `./infrastructure/k3s` directory. That works but is fragile (each Kustomization tries to manage every file there). The clean refactor is to split into subdirectories — `infrastructure/k3s/namespace/`, `infrastructure/k3s/data-layer/`, etc. — and add a `kustomization.yaml` to each. For Sprint 6 cutover you can ship the flat version; consolidate in Sprint 8.

### `clusters/ordinox-ai/apps.yaml`

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: ordinox-ai-apps
  namespace: flux-system
spec:
  interval: 5m
  dependsOn:
    - { name: ordinox-ai-data-layer }
    - { name: ordinox-ai-security }
  sourceRef:
    kind: GitRepository
    name: aia
  path: ./infrastructure/k3s   # or split agents into ./apps/ later
  prune: true
  wait: true
  timeout: 10m
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: echo-agent
      namespace: ordinox-ai
    - apiVersion: apps/v1
      kind: Deployment
      name: compliance-agent
      namespace: ordinox-ai
    - apiVersion: apps/v1
      kind: Deployment
      name: orchestrator-agent
      namespace: ordinox-ai
```

Commit + push:

```bash
git add clusters/ordinox-ai/
git commit -m "feat(flux): bootstrap ordinox-ai cluster managed dirs"
git push origin main
```

✅ Gate: `flux get kustomization -A` shows the new Kustomizations appearing within ~1 minute.

---

## Step 2 — Secrets (3 min) — manual, NOT via git

Secrets must NOT live in git. Create them out-of-band, *before* the Kustomizations that reference them reconcile.

```bash
# Postgres
kubectl create secret generic postgres-credentials \
  -n ordinox-ai \
  --from-literal=POSTGRES_DB=synthetic \
  --from-literal=POSTGRES_USER=synthetic \
  --from-literal=POSTGRES_PASSWORD="$(jq -r .pg_password ~/.aia/secrets/postgres.json)" \
  --dry-run=client -o yaml | kubectl apply -f -

# LLM API key
kubectl create secret generic llm-api-keys \
  -n ordinox-ai \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Long-term: replace the manual `kubectl create secret` with **SealedSecrets** (a `SealedSecret` resource committed to git that the controller decrypts in-cluster) or **External Secrets Operator** pulling from Vault. Sprint 8 hardening.

✅ Gate: both secrets present (`kubectl get secret -n ordinox-ai`).

---

## Step 3 — Watch the reconciliation (5 min)

```bash
# All Kustomizations should converge to READY=True in this order:
flux get kustomizations --watch
# Order: ordinox-ai-namespace → ordinox-ai-data-layer + ordinox-ai-security → ordinox-ai-apps

# If a Kustomization stays NotReady, check why:
flux get kustomization ordinox-ai-apps -A
flux events --for=Kustomization/ordinox-ai-apps -n flux-system
kubectl describe kustomization ordinox-ai-apps -n flux-system
```

Common failures and what they mean:

| Symptom | Likely cause | Fix |
|---|---|---|
| `dependency not ready` on `ordinox-ai-security` | sigstore or Kyverno HelmRelease still installing | wait; HelmReleases take 2–5 min on first install |
| `health check failed: deployment/echo-agent` | image not signed → policy-controller denied | check `kubectl get pods -n cosign-system -l name=webhook` logs |
| `failed to apply: namespaces "ordinox-ai" not found` | Kustomization ordering bug | confirm `dependsOn: [ordinox-ai-namespace]` set on others |
| `failed to apply ResourceQuota: forbidden` | namespace was created by ops with conflicting quota | resolve quota mismatch in capabilities.yaml or namespace.yaml |

✅ Gate: every Kustomization is `READY=True`, `STATUS="Applied revision: <sha>"`.

---

## Step 4 — Migration: audit_log direction='tool' (one-time, manual)

The schema migration in `infrastructure/k3s/migrations/0002_audit_tool.sql` can't be Flux-managed cleanly (Flux doesn't run SQL). One-off:

```bash
kubectl exec -n ordinox-ai postgres-0 -- \
  psql -U synthetic -d synthetic < infrastructure/k3s/migrations/0002_audit_tool.sql

# Verify
kubectl exec -n ordinox-ai postgres-0 -- \
  psql -U synthetic -d synthetic -c \
  "INSERT INTO audit_log (timestamp, agent_id, message_id, task_id, direction, message_type, status) VALUES (now(), 'preflight', 'mig-test', 'mig-test', 'tool', 'tool_call', 'ok'); DELETE FROM audit_log WHERE message_id='mig-test';"
```

For Sprint 8 production: wrap migrations in a Flux-managed `Job` resource (idempotent, runs once per migration version, gated by a checksum). Out of scope here.

✅ Gate: insert + delete succeed without constraint violation.

---

## Step 5 — RBAC drift audit (1 min)

```bash
bash scripts/security/audit_rbac.sh
# Expect: exit 0, "OK: deployed RBAC matches capabilities.yaml"
```

If drift appears here after Flux has reconciled, something raced — usually means an ops member ran `kubectl edit` between Flux pulls. Fix the YAML in git, push, let Flux reconcile. **Do not** `kubectl edit` to fix drift; that's a treadmill.

---

## Step 6 — Smoke tests (5 min)

```bash
# Echo Agent
kubectl run -n ordinox-ai smoke-echo \
  --rm -it --image=redis:7-alpine --restart=Never \
  -- redis-cli -h redis.ordinox-ai.svc.cluster.local <<EOF
XADD agent:echo:tasks * from_agent smoke to_agent echo-agent-v1 task_id smoke-1 message_type echo status pending data {} metadata {}
SLEEP 2
XREAD COUNT 1 STREAMS agent:echo:results 0
EOF

# Orchestrator (requires ANTHROPIC_API_KEY in llm-api-keys)
kubectl exec -n ordinox-ai deploy/orchestrator-agent -- \
  curl -sS -X POST http://localhost:8000/requests \
  -H 'content-type: application/json' \
  -d '{"user_request":"Draft a vanilla NDA","project_id":"smoke-3"}'
```

✅ Gate: echo replies within 2s; orchestrator returns 200 with `escalated=false`.

---

## Step 7 — Security E2E tests (3 min)

```bash
pytest tests/security -m security --tb=short
```

The security tests use the active `KUBECONFIG`. Expect all to pass (the namespace, NetworkPolicies, RBAC, and admission controllers are all live now).

---

## Rollback

### Pause Flux without losing state

```bash
# Stop reconciling a specific Kustomization (the resources stay deployed)
flux suspend kustomization ordinox-ai-apps -n flux-system

# Now you can hand-edit if needed, or revert in git
# When ready:
flux resume kustomization ordinox-ai-apps -n flux-system
```

### Roll back to a previous commit

```bash
# 1. Identify the bad commit
git log --oneline -- clusters/ordinox-ai/ infrastructure/

# 2. Revert
git revert <bad-sha>
git push origin main

# 3. Force Flux to reconcile immediately (don't wait for next poll)
flux reconcile source git aia -n flux-system
flux reconcile kustomization ordinox-ai-apps -n flux-system
```

### Nuke and reapply

If you need to delete everything Flux is managing and let it re-reconcile from scratch:

```bash
# CAREFUL: this deletes all resources owned by that Kustomization
kubectl delete kustomization ordinox-ai-apps -n flux-system
# Then re-add via git revert / push, OR:
kubectl apply -f clusters/ordinox-ai/apps.yaml   # bootstrap-style, exception to the no-out-of-band rule
```

---

## Known not-yet-supported in staging (carries from Sprint 6 audit)

- **Sprint 3 (Gemini)** — Qdrant + Milvus + Analyst Agent RAG. Don't add their Flux Kustomization until Gemini fixes the `faiss_store.py` `pickle.load()` CWE-502 finding (`claude-code/handoff/SPRINT-3-SECURITY-FINDINGS.md`).
- **Sprint 4/5 (Cursor)** — frontend / editor / WebSocket ingress. When Cursor's manifests land, add a `clusters/ordinox-ai/frontend.yaml` Kustomization with `dependsOn: [ordinox-ai-apps]`.
- **Sprint 7 (ChatGPT)** — `compliance-service` Deployment lacks hardened `securityContext`. Kyverno will reject it. ChatGPT must add `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, capability drops to their pod spec before their Kustomization can reconcile cleanly.

---

## Done criteria

Sprint 6 Flux deploy is considered complete when:

1. All 4 Kustomizations (`ordinox-ai-namespace`, `-data-layer`, `-security`, `-apps`) report `READY=True`.
2. `bash scripts/security/audit_rbac.sh` exits 0.
3. `pytest tests/security -m security` reports 0 unexpected failures.
4. Smoke tests in Step 6 pass.
5. `git log --oneline clusters/ordinox-ai/` shows a clean history with no out-of-band-fix revert commits.

At that point, page the team for production-deploy readiness review.

---

## When to use this runbook vs the kubectl one

| Use the Flux runbook | Use the kubectl runbook |
|---|---|
| Cluster has Flux controllers healthy | No Flux installed (k3d, kind, fresh kubeadm) |
| Long-term staging / prod | Local dev (`scripts/talos-local-dev-cluster.sh`) |
| Multiple operators touching the cluster (Flux is the conflict resolver) | Single-operator ad-hoc experimentation |
| You want git-history audit of every change | You want a temporary diagnostic state |

Don't run both against the same cluster.
