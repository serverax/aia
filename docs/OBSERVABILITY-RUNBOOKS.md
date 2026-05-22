# Observability Runbooks — ordinox-ai

One section per alert defined in `infrastructure/compliance/prometheus-rules.yaml`. Each section is anchored so the `runbook_url` annotation in the alert resolves to the right doc.

Use this when a page fires. Read the **Symptoms** to confirm you're in the right runbook, then **Diagnose** to find the root cause, then **Fix** to act.

For all alerts: the namespace is `ordinox-ai` unless noted. Examples assume `KUBECONFIG` points at the cluster.

---

## Table of contents

- [Policy drift](#policy-drift)
  - [NetworkPolicyCountChanged](#networkpolicycountchanged)
  - [RBACDriftDetected](#rbacdriftdetected)
- [Pod health](#pod-health)
  - [PodCrashLooping](#podcrashlooping)
  - [PodImagePullFailing](#podimagepullfailing)
  - [PodNotReady](#podnotready)
- [Compliance service](#compliance-service)
  - [ComplianceDecisionLatencyP99High](#compliancedecisionlatencyp99high)
  - [ComplianceErrorRateHigh](#complianceerrorratehigh)
  - [ComplianceThroughputDrop](#compliancethroughputdrop)
  - [NoComplianceMetrics](#nocompliancemetrics)
- [Audit log](#audit-log)
  - [AuditLogSilence](#auditlogsilence)
  - [BulkComplianceRejections](#bulkcompliancerejections)
- [Resources](#resources)
  - [PodCPUUsageHigh](#podcpuusagehigh)
  - [PodMemoryUsageHigh](#podmemoryusagehigh)
  - [PersistentVolumeAlmostFull](#persistentvolumealmostfull)
- [Metric inventory — what needs to be exposed](#metric-inventory)

---

## Policy drift

### NetworkPolicyCountChanged

**Symptoms.** Alert fires when `count(kube_networkpolicy_created{namespace="ordinox-ai"}) != 6` for 5+ minutes.

**Why 6?** `infrastructure/k3s/namespace.yaml` ships 2 baseline policies (`default-deny-all` + `allow-internal`). `scripts/security/generate_policies.py` emits 4 per-agent egress policies (one each for `echo`, `orchestrator`, `compliance`, `analyst`). Total: 6.

**Diagnose.**
```bash
# What's actually there?
kubectl get networkpolicy -n ordinox-ai
# Expected names: default-deny-all, allow-internal,
#   echo-agent-egress, orchestrator-agent-egress,
#   compliance-agent-egress, analyst-agent-egress

# What does the repo say should be there?
git ls-files infrastructure/k3s/network-policies-per-agent.yaml
yq '.metadata.name' infrastructure/k3s/network-policies-per-agent.yaml
```

**Root causes.**
- Someone ran `kubectl delete networkpolicy <name>` directly.
- A Flux Kustomization was deleted, taking the policies with it (prune=true).
- A new policy was added out-of-band and the count is now 7.

**Fix.**
1. If a policy was deleted: re-apply via Flux (`flux reconcile kustomization ordinox-ai-security`) or kubectl.
2. If an extra policy exists: either delete it or add it to `capabilities.yaml` so audit_rbac stops flagging it too.
3. If the baseline count is wrong (we genuinely now have N agents instead of 4), update the alert threshold to match.

---

### RBACDriftDetected

**Symptoms.** Alert fires when `aia_rbac_audit_exit_code > 0` for 5+ minutes. This metric comes from the nightly CronJob that runs `scripts/security/audit_rbac.sh` — see [Metric inventory](#metric-inventory).

**Diagnose.**
```bash
# Run the audit interactively to see WHICH resources drifted
bash scripts/security/audit_rbac.sh
# Findings printed as MISSING / EXTRA / MISMATCH with remediation hints.
```

**Root causes.**
- `kubectl edit role/rolebinding` out-of-band — classic case.
- A Helm chart from another team created extra RBAC inside `ordinox-ai`.
- The generator was re-run with a new `capabilities.yaml` but the regenerated YAML wasn't applied.

**Fix.**
- If drift is **MISSING**: regenerate + reapply: `python scripts/security/generate_policies.py && kubectl apply -f infrastructure/k3s/rbac-per-agent.yaml`.
- If drift is **EXTRA** and intentional: add the resource to `capabilities.yaml`.
- If drift is **MISMATCH**: re-apply the generated YAML (overwrites hand-edits).

---

## Pod health

### PodCrashLooping

**Symptoms.** A container restarted more than 3 times in the last 15 minutes. Almost always CrashLoopBackOff.

**Diagnose.**
```bash
kubectl get pods -n ordinox-ai | grep -v Running
kubectl describe pod <pod> -n ordinox-ai | tail -30   # look at Events
kubectl logs <pod> -n ordinox-ai --previous --tail=100
```

**Root causes (in rough order of frequency).**
- App bug — uncaught exception on startup. Logs show the stack trace.
- Wrong env var or missing Secret/ConfigMap — `CreateContainerConfigError` in Events.
- Liveness probe too aggressive — pod gets killed before it finishes warming.
- OOMKill — see [PodMemoryUsageHigh](#podmemoryusagehigh).

**Fix.** Depends on root cause. If it's the agent we ship, the fix is a code change + new image + redeploy. If it's a probe issue, edit the Deployment.

---

### PodImagePullFailing

**Symptoms.** Pod stuck in `ImagePullBackOff` or `ErrImagePull` for 5+ minutes.

**Diagnose.**
```bash
kubectl describe pod <pod> -n ordinox-ai | grep -A5 'Failed'
# Look at the exact registry/image/tag in the error message.

# If GHCR auth: check the imagePullSecret
kubectl get secret ghcr-credentials -n ordinox-ai -o yaml | head -10

# If sigstore policy-controller rejected the image:
kubectl -n cosign-system logs -l app.kubernetes.io/name=policy-controller --tail=50 | grep -i denied
```

**Root causes.**
- Image tag doesn't exist (`:latest` removed, new SHA not yet pushed by CI).
- `imagePullSecret` missing or expired.
- sigstore `ClusterImagePolicy` denied because the image isn't cosign-signed. **Most common in this cluster** — see Sprint 6 sigstore install.
- Network: cluster can't reach `ghcr.io`. Rare unless egress firewall.

**Fix.**
- Missing image: push it, or revert to a known-good tag.
- Auth: `kubectl create secret docker-registry ghcr-credentials -n ordinox-ai --docker-server=ghcr.io --docker-username=... --docker-password=...`
- Signing: re-build via CI matrix (signs with cosign as part of the job).

---

### PodNotReady

**Symptoms.** Pod's readiness probe has been false for 10+ minutes. Service traffic isn't routed to it.

**Diagnose.**
```bash
kubectl describe pod <pod> -n ordinox-ai | grep -A3 'Readiness'
# Then check the actual probe target:
kubectl exec -n ordinox-ai <pod> -- wget -qO- http://localhost:<port>/ready
```

**Root causes.**
- App started but a dependency (Redis, Postgres) is unreachable — common after data-layer restarts.
- Probe spec points at the wrong port or path.
- Liveness probe is more permissive than readiness (pod stays alive but never marks ready) — design smell.

**Fix.**
- Restore the dependency.
- Fix the probe path/port in the Deployment manifest, redeploy.

---

## Compliance service

### ComplianceDecisionLatencyP99High

**Symptoms.** 99th-percentile decision latency above 100ms over the last 5 minutes.

**Diagnose.**
```bash
# Check Qdrant latency (Sprint 3 RAG path); compliance decisions wait on it.
kubectl exec -n ordinox-ai deploy/qdrant -- curl -s http://localhost:6333/metrics | grep -i latency

# Check Postgres connection pool saturation
kubectl exec -n ordinox-ai postgres-0 -- \
  psql -U synthetic -d synthetic -c "SELECT count(*) FROM pg_stat_activity;"
```

**Root causes.**
- Qdrant query slowness (large collection, index rebuild).
- Postgres connection pool exhausted — agent waits for a connection.
- Compliance Officer's keyword evaluation regex got pathological (unlikely with current rules).

**Fix.**
- Scale up Qdrant (more replicas) or rebuild the index.
- Bump Postgres `max_connections` or the agent's pool size.
- If the agent code is at fault, profile and patch.

---

### ComplianceErrorRateHigh

**Symptoms.** More than 1% of compliance decisions returning `status="error"` over 5 minutes. Critical.

**Diagnose.**
```bash
kubectl logs -n ordinox-ai -l app=compliance-agent --tail=200 | grep -i error
# Look for the specific exception class.
```

**Root causes.**
- Anthropic API outage if compliance is calling Claude (it doesn't in Sprint 2 placeholder, but will once Sprint 3 RAG is wired).
- Malformed input from orchestrator (a recent decomposer change emitting unexpected fields).
- Qdrant unavailable, causing the RAG lookup path to throw.

**Fix.** Stop the bleed if possible (revert the bad change), then dig into the specific error class. Add input validation if it's an upstream schema break.

---

### ComplianceThroughputDrop

**Symptoms.** Decision rate dropped >20% vs the same window 1 hour ago, sustained for 10 minutes.

**Diagnose.**
```bash
# Is it actually quiet, or is something jammed?
kubectl exec -n ordinox-ai deploy/redis -- \
  redis-cli XLEN agent:compliance_officer:tasks
# >0 with no decisions = stuck. ~0 with no decisions = genuinely quiet.

# Orchestrator dispatching?
kubectl logs -n ordinox-ai -l app=orchestrator-agent --tail=50 | grep -i dispatch
```

**Root causes.**
- Genuinely quiet period — false alarm. Verify upstream request volume.
- Upstream orchestrator stuck (look at orchestrator's own metrics).
- Compliance agent pods all unhealthy but not yet flagged by `PodNotReady` (would need 10m).

**Fix.** Identify which side the jam is on (Redis stream length is the cheapest signal), unjam.

---

### NoComplianceMetrics

**Symptoms.** `compliance_decisions_total` metric is absent for 10+ minutes. Catches "deployed but the metrics exporter isn't wired up" silently-broken setups.

**Diagnose.**
```bash
# Is the pod running?
kubectl get pod -n ordinox-ai -l app=compliance-agent

# Is the ServiceMonitor present? (needed for Prometheus to scrape)
kubectl get servicemonitor -n ordinox-ai compliance-agent -o yaml

# Can we hit /metrics on the pod directly?
kubectl exec -n ordinox-ai deploy/compliance-agent -- curl -s http://localhost:8000/metrics | head -20
```

**Root causes.**
- Compliance Officer doesn't actually export `compliance_decisions_total` yet — Sprint 6 ships the placeholder agent without metrics; Sprint 7/8 wires them. **Expected to fire during early staging.**
- ServiceMonitor missing (Prometheus doesn't know to scrape).
- Pod running but on a port that isn't `/metrics`-enabled.

**Fix.** Wire the metric. See [Metric inventory § compliance_decisions_total](#metric-inventory) for the implementation sketch.

---

## Audit log

### AuditLogSilence

**Symptoms.** No `audit_log` table inserts in 10+ minutes.

**Diagnose.**
```bash
# Direct check: are there any recent rows?
kubectl exec -n ordinox-ai postgres-0 -- \
  psql -U synthetic -d synthetic -c \
  "SELECT max(timestamp) FROM audit_log;"

# If max is recent: the metric source is wrong, not the system.
# If max is stale: nothing is auditing.

# Are the agents running?
kubectl get pods -n ordinox-ai -l app=echo-agent
kubectl get pods -n ordinox-ai -l app=compliance-agent

# Are they processing tasks at all?
kubectl exec -n ordinox-ai deploy/redis -- \
  redis-cli XLEN agent:echo:tasks
kubectl exec -n ordinox-ai deploy/redis -- \
  redis-cli XLEN orchestrator:replies
```

**Root causes.**
- Genuinely no traffic (verify against request volume / orchestrator metrics).
- Agents are processing but the audit Postgres write is silently failing — check agent logs for `audit write failed`.
- `audit_log_inserts_total` exporter is broken; the table is fine.

**Fix.** Distinguish "no traffic" from "audit broken" first. If audit-broken, check Postgres connectivity from the agent pods.

---

### BulkComplianceRejections

**Symptoms.** Compliance Officer rejected >10 requests in 1 minute. Possible attack pattern OR upstream pushing malformed data OR a rule update gone too wide.

**Diagnose.**
```bash
# Pull recent rejections from the audit log
kubectl exec -n ordinox-ai postgres-0 -- \
  psql -U synthetic -d synthetic -c \
  "SELECT timestamp, agent_id, task_id, payload->>'rationale' AS reason
   FROM audit_log
   WHERE direction='out' AND payload->>'verdict'='rejected'
   ORDER BY timestamp DESC LIMIT 20;"
```

**Root causes.**
- An attacker is throwing many requests with violation-keyword payloads (current Sprint 2 placeholder rules: "violation", "without consent", etc.).
- The orchestrator's task_decomposer started emitting task descriptions that always trigger reject rules.
- A new compliance rule was deployed that's too aggressive.

**Fix.**
- If it's an attack: rate-limit at the orchestrator's request stream OR the API gateway.
- If decomposer is at fault: roll back the recent orchestrator change.
- If rule update is at fault: revert capabilities/rule change.

---

## Resources

### PodCPUUsageHigh

**Symptoms.** A pod has used >80% of its CPU limit for 10+ minutes.

**Diagnose.**
```bash
kubectl top pods -n ordinox-ai
kubectl describe pod <pod> -n ordinox-ai | grep -A2 'Limits:'
```

**Fix.**
- Bump the `resources.limits.cpu` in the Deployment.
- OR investigate why the agent is burning cycles — likely a hot loop or unbounded retry.

---

### PodMemoryUsageHigh

**Symptoms.** A pod has used >85% of its memory limit for 10+ minutes. At 100% the kernel OOMKills.

**Diagnose.**
```bash
kubectl top pods -n ordinox-ai
# Trend over the last hour — is it growing? (likely a leak)
# In Grafana: container_memory_working_set_bytes for this pod
```

**Fix.**
- Short-term: bump `resources.limits.memory`.
- Long-term: if it's a leak (memory grows monotonically), the agent code has a leak — must fix. Common culprits: unbounded asyncio task lists, unclosed Redis connections, Pydantic model accumulation.

---

### PersistentVolumeAlmostFull

**Symptoms.** A PVC in `ordinox-ai` is >90% full. At 100% writes fail — Postgres can corrupt, Redis appendonly file refuses appends.

**Diagnose.**
```bash
kubectl exec -n ordinox-ai postgres-0 -- df -h /var/lib/postgresql/data
kubectl exec -n ordinox-ai redis-0    -- df -h /data
```

**Root causes.**
- audit_log table growing without retention. By 2026 standards we expect ~1KB/row; busy day = millions of rows.
- Redis appendonly file unbounded.
- Container logs unbounded (less likely with read-only root FS).

**Fix.**
- **Postgres**: archive then `DELETE FROM audit_log WHERE timestamp < now() - interval '90 days'; VACUUM FULL;`. Or grow the PVC.
- **Redis**: set `appendonly-truncate-keep-segments` policy, or grow the PVC.
- Grow PVC: `kubectl edit pvc data-postgres-0` then bump `resources.requests.storage`. Requires the StorageClass to allow expansion.

---

## Metric inventory

The alerts depend on several metrics that aren't yet exposed by the agents or by built-in exporters. Each needs a one-time wire-up before its alert is meaningful. Until wired, the alert evaluates to no-data — `NoComplianceMetrics` catches this for the compliance metric specifically.

| Metric | Type | Source | Implementation |
|---|---|---|---|
| `kube_networkpolicy_created` | gauge | kube-state-metrics (built-in to kube-prometheus-stack) | ✅ Already there |
| `kube_pod_status_*`, `kube_pod_container_status_*` | gauge | kube-state-metrics | ✅ Already there |
| `container_cpu_usage_seconds_total`, `container_memory_working_set_bytes` | counter/gauge | cAdvisor (built-in to kubelet) | ✅ Already there |
| `kubelet_volume_stats_*` | gauge | kubelet | ✅ Already there |
| `aia_rbac_audit_exit_code` | gauge | **CronJob — see below** | ❌ TODO |
| `compliance_decision_duration_seconds` | histogram | **compliance_agent /metrics endpoint** | ❌ TODO |
| `compliance_decisions_total{status,verdict}` | counter | compliance_agent /metrics | ❌ TODO |
| `aia_audit_log_inserts_total{direction}` | counter | **postgres_exporter custom query** | ❌ TODO |
| `aia_orchestrator_escalations_pending` | gauge | orchestrator /metrics | ❌ TODO |

### RBAC drift exporter (CronJob spec)

The audit script returns exit 0/1/2; we wrap it in a CronJob that pushes the exit code to a Prometheus pushgateway. Approximate spec:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: rbac-audit
  namespace: ordinox-ai
spec:
  schedule: "*/15 * * * *"   # every 15 min
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: rbac-auditor-sa    # cluster-read RBAC scoped to SAs/Roles
          restartPolicy: OnFailure
          containers:
            - name: audit
              image: ghcr.io/serverax/aia/audit-runner:latest    # CI builds this
              command: ["/bin/bash", "-c"]
              args:
                - |
                  set +e
                  python -m scripts.security.audit_rbac
                  EXIT=$?
                  echo "aia_rbac_audit_exit_code $EXIT" \
                    | curl --data-binary @- \
                      http://prometheus-pushgateway.monitoring.svc.cluster.local:9091/metrics/job/rbac-audit
```

The `audit-runner` image needs Python + the repo's `scripts/` and `infrastructure/security/capabilities.yaml` baked in.

### compliance_agent /metrics endpoint

The agent's `main.py` should add a `/metrics` route returning Prometheus exposition format. Easiest via `prometheus_client`:

```python
from prometheus_client import Counter, Histogram, generate_latest

DECISIONS = Counter("compliance_decisions_total", "Compliance decisions", ["status", "verdict"])
LATENCY = Histogram("compliance_decision_duration_seconds", "Decision latency")

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

Plus a `ServiceMonitor` so Prometheus picks it up:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: compliance-agent
  namespace: ordinox-ai
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: compliance-agent
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

Same pattern for `orchestrator_agent` (`aia_orchestrator_escalations_pending`).

### Postgres audit_log row-counter

Add a custom query to `postgres_exporter` that exposes audit_log inserts as a Prometheus counter (well, gauge of cumulative count — the alert uses `rate()`):

```yaml
# postgres_exporter ConfigMap
aia_audit_log_inserts_total:
  query: |
    SELECT direction, count(*) AS total
    FROM audit_log
    GROUP BY direction
  metrics:
    - direction:
        usage: "LABEL"
        description: "in / out / tool"
    - total:
        usage: "COUNTER"
        description: "Cumulative audit_log inserts by direction"
```

Wire this into the postgres_exporter sidecar in `infrastructure/k3s/postgres.yaml` (Sprint 7 hardening can productionize the exporter).

---

## When to suppress vs page

| Alert | Page (on-call) | Slack-only |
|---|---|---|
| `PodImagePullFailing` | ✅ during business hours | ❌ after hours (won't recover overnight) |
| `PodCrashLooping` | ✅ critical | |
| `ComplianceErrorRateHigh` | ✅ critical | |
| `PodMemoryUsageHigh` | ✅ critical | |
| `PersistentVolumeAlmostFull` | ✅ critical (will lead to outage) | |
| `BulkComplianceRejections` | ✅ may be attack | |
| `NetworkPolicyCountChanged` | ❌ warning | ✅ |
| `RBACDriftDetected` | ❌ warning | ✅ |
| `ComplianceDecisionLatencyP99High` | ❌ warning | ✅ |
| `ComplianceThroughputDrop` | ❌ warning | ✅ |
| `NoComplianceMetrics` | ❌ warning | ✅ (until metrics are wired) |
| `AuditLogSilence` | ❌ warning | ✅ |
| `PodNotReady` | ❌ warning | ✅ |
| `PodCPUUsageHigh` | ❌ warning | ✅ |

Alertmanager routing config lives in your Prometheus install's values; configure routes based on `severity` label.
