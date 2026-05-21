# Staging Deployment Runbook

Ordered checklist for deploying to a staging Kubernetes cluster. Each step
has a verification gate; do **not** proceed if a gate fails. Rollback steps
are at the bottom.

> **Cluster prerequisite reality check** (as of 2026-05-21):
> - Hetzner cluster at `148.251.247.56` is unreachable (SSH refused; Talos doesn't have sshd anyway — see `provision-cluster-full.sh` deprecation banner).
> - WSL/Talos cluster ops is bringing up — use `talosctl kubeconfig` to grab credentials.
> - All Sprint 6 manifests target namespace `synthetic-enterprise`.
> - This runbook assumes the cluster CNI **enforces** NetworkPolicy. See `docs/NETWORK-POLICY-TROUBLESHOOTING.md` § Step 0 to verify before applying anything.

---

## Step 0 — Preflight checks (5 min)

```bash
export KUBECONFIG=~/.kube/aia-config.yaml   # or talosctl-issued config

# 0.1 Context + connectivity
kubectl config current-context
kubectl get nodes -o wide          # expect Ready
kubectl get ns                     # expect synthetic-enterprise OR be ready to create

# 0.2 CNI enforces NetworkPolicy?
# See docs/NETWORK-POLICY-TROUBLESHOOTING.md § Step 0 for the deny-all probe.
# If your CNI doesn't enforce, STOP — Sprint 6 policies will be inert.

# 0.3 Vault unsealed?
kubectl -n vault exec vault-0 -- vault status | grep -E 'Initialized|Sealed'
# Expect: Initialized: true, Sealed: false
# If sealed: follow infrastructure/vault/PREFLIGHT-UNSEAL.md

# 0.4 Image registry creds (needed for the agent images)
kubectl get secret ghcr-credentials -n synthetic-enterprise 2>&1 \
  || echo "MISSING — create with: kubectl create secret docker-registry ghcr-credentials ..."
```

✅ Gate: every command returns successfully. If 0.2 fails, stop and fix CNI first.

---

## Step 1 — Namespace + agent-sa + baseline NetworkPolicies (2 min)

```bash
kubectl apply -f infrastructure/k3s/namespace.yaml

# Verify
kubectl get ns synthetic-enterprise -o jsonpath='{.metadata.labels}' ; echo
kubectl get sa agent-sa -n synthetic-enterprise
kubectl get networkpolicy -n synthetic-enterprise
# Expect: default-deny-all + allow-internal
```

✅ Gate: `agent-sa` exists; two baseline NetworkPolicies present.

---

## Step 2 — Secrets (3 min)

The runbook does NOT commit secret values. Source them from `~/.aia/secrets/` (Sprint 1 + 6 preflight outputs) or your secret manager.

```bash
# 2.1 Postgres credentials (Sprint 1 schema)
# Either reuse the inline Secret in postgres.yaml after editing REPLACE_ME_BEFORE_APPLY,
# or apply your own Secret:
kubectl create secret generic postgres-credentials \
  -n synthetic-enterprise \
  --from-literal=POSTGRES_DB=synthetic \
  --from-literal=POSTGRES_USER=synthetic \
  --from-literal=POSTGRES_PASSWORD="$(jq -r .pg_password ~/.aia/secrets/postgres.json)" \
  --dry-run=client -o yaml | kubectl apply -f -

# 2.2 LLM API key (Sprint 2 dep, used by orchestrator + analyst)
kubectl create secret generic llm-api-keys \
  -n synthetic-enterprise \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

# Verify
kubectl get secret -n synthetic-enterprise | grep -E 'postgres-credentials|llm-api-keys'
```

✅ Gate: both secrets present. Never log the values.

---

## Step 3 — Data layer (5 min)

```bash
kubectl apply -f infrastructure/k3s/postgres.yaml
kubectl apply -f infrastructure/k3s/redis.yaml
kubectl apply -f infrastructure/k3s/jaeger.yaml

# Wait for the StatefulSets to come up
kubectl rollout status statefulset/postgres  -n synthetic-enterprise --timeout=5m
kubectl rollout status statefulset/redis     -n synthetic-enterprise --timeout=3m
kubectl rollout status deployment/jaeger     -n synthetic-enterprise --timeout=3m

# 3.1 Apply audit_log migration (Sprint 6 added direction='tool')
kubectl exec -n synthetic-enterprise postgres-0 -- \
  psql -U synthetic -d synthetic < infrastructure/k3s/migrations/0002_audit_tool.sql
```

✅ Gate: 3 pods Running; audit_log accepts `direction='tool'` rows.

```bash
# Smoke test the migration
kubectl exec -n synthetic-enterprise postgres-0 -- \
  psql -U synthetic -d synthetic -c \
  "INSERT INTO audit_log (timestamp, agent_id, message_id, task_id, direction, message_type, status) VALUES (now(), 'preflight', 'mig-test', 'mig-test', 'tool', 'tool_call', 'ok'); DELETE FROM audit_log WHERE message_id='mig-test';"
```

---

## Step 4 — Sprint 6 admission controllers (10 min)

```bash
# Follow infrastructure/security/INSTALL.md sequentially:
#   - sigstore/policy-controller
#   - Kyverno
#   - actions-runner-controller (only if CI matrix is hitting this cluster)

# Verify ClusterImagePolicy + Kyverno ClusterPolicies present
kubectl get clusterimagepolicy aia-images-must-be-signed
kubectl get clusterpolicy aia-readonly-root-fs aia-drop-all-capabilities aia-no-host-mounts aia-no-privilege-escalation

# Smoke test: unsigned image is rejected
pytest tests/security/test_admission_rejects_unsigned.py -v
```

✅ Gate: admission test passes; unsigned `nginx:latest` is denied.

---

## Step 5 — Sprint 6 per-agent policies (3 min)

```bash
# These are AUTOGENERATED from infrastructure/security/capabilities.yaml.
# If you need to edit, do it in capabilities.yaml and re-run:
#   python scripts/security/generate_policies.py
# Hand-edits to the generated files will be flagged by audit_rbac.sh.

kubectl apply -f infrastructure/k3s/network-policies-per-agent.yaml
kubectl apply -f infrastructure/k3s/rbac-per-agent.yaml

# Verify drift-free
bash scripts/security/audit_rbac.sh
# Expect: exit 0, "OK: deployed RBAC matches capabilities.yaml"
```

✅ Gate: audit_rbac exit code 0.

---

## Step 6 — Agent images (5 min)

Images must be signed (Sprint 6 sigstore policy denies unsigned).
If CI is configured (`.github/workflows/ci.yml`'s `build-images` job), the
images already exist in GHCR with cosign signatures. Otherwise build + sign
locally first.

```bash
# Confirm image SHAs are reachable + signed
for image in echo-agent orchestrator-agent compliance-agent analyst-agent; do
  cosign verify-blob \
    --key /etc/aia-cosign/cosign.pub \
    --signature <(crane manifest ghcr.io/serverax/aia/${image}:latest | jq -r .annotations.\"dev.sigstore.cosign/signature\") \
    <(crane manifest ghcr.io/serverax/aia/${image}:latest) \
    && echo "${image} signed" || echo "${image} UNSIGNED — fix CI before continuing"
done
```

✅ Gate: all 4 images verify.

---

## Step 7 — Agent deployments (5 min)

Order: data-layer-dependent → orchestrator → tool-using agents → echo.

```bash
# Sprint 1 PoC
kubectl apply -f infrastructure/k3s/echo-agent.yaml
kubectl rollout status deployment/echo-agent -n synthetic-enterprise --timeout=3m

# Sprint 2 — Compliance Officer skeleton
kubectl apply -f infrastructure/k3s/compliance-agent.yaml
kubectl rollout status deployment/compliance-agent -n synthetic-enterprise --timeout=3m

# Sprint 2 — Orchestrator (depends on llm-api-keys + compliance agent up)
kubectl apply -f infrastructure/k3s/orchestrator-agent.yaml
kubectl rollout status deployment/orchestrator-agent -n synthetic-enterprise --timeout=5m

# Sprint 3 — Analyst Agent (deploy only after Gemini ships Sprint 3 RAG stack)
# Skip in staging until Sprint 3's manifests + Qdrant/Milvus are ready.
```

✅ Gate: all 3 deployed agents show `Available True` + 0 restarts after 60s.

```bash
kubectl get deploy -n synthetic-enterprise -o wide
kubectl get pods -n synthetic-enterprise -o wide
kubectl get events -n synthetic-enterprise --sort-by='.lastTimestamp' | tail -20
```

---

## Step 8 — End-to-end smoke (5 min)

```bash
# 8.1 Echo Agent loop
kubectl run -n synthetic-enterprise smoke-probe \
  --rm -it --image=redis:7-alpine --restart=Never \
  -- redis-cli -h redis.synthetic-enterprise.svc.cluster.local <<EOF
XADD agent:echo:tasks * from_agent smoke to_agent echo-agent-v1 task_id smoke-1 message_type echo status pending data {} metadata {}
SLEEP 2
XREAD COUNT 1 STREAMS agent:echo:results 0
EOF
# Expect: a matching ECHO reply within 2 seconds.

# 8.2 Compliance Officer
kubectl run -n synthetic-enterprise compliance-probe \
  --rm -it --image=redis:7-alpine --restart=Never \
  -- redis-cli -h redis.synthetic-enterprise.svc.cluster.local <<EOF
XADD agent:compliance_officer:tasks * from_agent smoke to_agent compliance_officer task_id smoke-2 message_type task_assignment status in_progress data {"description":"safe NDA review"} metadata {}
SLEEP 2
XREAD COUNT 1 STREAMS orchestrator:replies 0
EOF
# Expect: verdict=approved, risk_level=green within 2 seconds.

# 8.3 Orchestrator end-to-end (requires ANTHROPIC_API_KEY in llm-api-keys)
kubectl exec -n synthetic-enterprise deploy/orchestrator-agent -- \
  curl -sS -X POST http://localhost:8000/requests \
  -H 'content-type: application/json' \
  -d '{"user_request":"Draft a vanilla NDA","project_id":"smoke-3"}'
# Expect: 200 with task_count >= 1 and escalated=false.
```

✅ Gate: all three smoke tests succeed.

---

## Step 9 — Final audit (2 min)

```bash
# RBAC drift check
bash scripts/security/audit_rbac.sh

# Security E2E tests
pytest tests/security -m security --tb=short

# Recent events should be clean
kubectl get events -n synthetic-enterprise --field-selector type=Warning --sort-by='.lastTimestamp' | tail -10
```

✅ Gate: zero drift, all security tests pass or skip (skips OK if optional policies aren't applied yet), no recent Warning events.

---

## Rollback

If anything in steps 4–7 goes sideways:

```bash
# Quickest rollback — delete the failed component, leave the rest
kubectl delete deployment <name> -n synthetic-enterprise

# Full Sprint 6 controller rollback (keeps data layer + agents)
kubectl delete clusterimagepolicy aia-images-must-be-signed
kubectl delete clusterpolicy aia-readonly-root-fs aia-drop-all-capabilities aia-no-host-mounts aia-no-privilege-escalation aia-require-signed-image-pattern
kubectl delete -f infrastructure/k3s/network-policies-per-agent.yaml
kubectl delete -f infrastructure/k3s/rbac-per-agent.yaml
helm uninstall policy-controller -n cosign-system
helm uninstall kyverno -n kyverno

# Data layer rollback (destructive — wipes Postgres volume!)
# Only do this if the cluster needs a clean reset.
kubectl delete -f infrastructure/k3s/postgres.yaml -f infrastructure/k3s/redis.yaml
kubectl delete pvc -n synthetic-enterprise --all
```

---

## Known not-yet-supported in staging (carries from Sprint 6 audit)

- **Sprint 3 (Gemini)** — Qdrant + Milvus + Analyst Agent's RAG layer. Do not apply Sprint 3 manifests in staging until Gemini fixes the `pickle.load()` finding in `services/semantic_search/vector_store/faiss_store.py` (see `claude-code/handoff/SPRINT-3-SECURITY-FINDINGS.md`).
- **Sprint 4/5 (Cursor)** — frontend / editor / WebSocket ingress. Not yet integrated; staging deploys backend-only.
- **Sprint 7 (ChatGPT) — `compliance-service`** — observed during cluster trials to fail PodSecurity admission because its Deployment YAML lacks `allowPrivilegeEscalation: false` + capability drops. ChatGPT must harden its Deployment before applying. The Kyverno policies (Step 4) will reject the pod outright otherwise.

---

## When this runbook is "done"

Sprint 6 deploy is considered complete when:

- All gates in Steps 0–9 pass on the staging cluster.
- `bash scripts/security/audit_rbac.sh` exits 0.
- `pytest -m security` reports 0 unexpected failures.
- Smoke test 8.3 (orchestrator) returns a non-escalated response for a benign request.

At that point, page the team for production-deployment readiness review.
