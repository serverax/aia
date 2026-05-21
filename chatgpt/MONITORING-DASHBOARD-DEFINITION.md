# PHASE 2 MONITORING DASHBOARD

## Purpose

This document defines what Ops and ChatGPT watch during Phase 2 execution. It provides real commands, thresholds, and alert actions for load testing, backend health, and SLA tracking.

## Dashboard 1: Load Test Metrics

Use during `run_load_test.ps1`.

Metrics:

- current requests per second
- p50 latency
- p95 latency
- p99 latency
- error rate
- backend CPU
- backend memory
- pod restarts

Alert thresholds:

| Metric | Warn | Escalate | Rationale |
| --- | --- | --- | --- |
| p95 latency | `> 3s` | `> 5s` | 3s indicates degradation; 5s violates user workflow expectations |
| error rate | `> 5%` | `> 10%` | 5% suggests instability; 10% stops test |
| backend CPU | `> 90%` | sustained `> 95%` | CPU saturation predicts latency spike |
| backend memory | `> 85%` | OOM/restarts | memory pressure can crash pods |
| pod restarts | any restart | repeated restarts | any restart invalidates clean load evidence |

Real-time log command:

```bash
watch -n 5 'tail -40 /tmp/phase2-load-test.log | grep -E "Aggregated|GET|POST|fail|Error|p95"'
```

Kubernetes resource commands:

```bash
kubectl top nodes
kubectl top pods -n synthetic-enterprise --containers
kubectl -n synthetic-enterprise get pods -o wide
kubectl -n synthetic-enterprise get events --sort-by=.lastTimestamp | tail -20
```

Validation gate:

```bash
grep -E "Aggregated|GET|POST" /tmp/phase2-load-test.log
```

If the log has no Locust summary lines after 2 minutes, monitoring is not capturing correctly. Stop and fix logging before continuing.

## Dashboard 2: Backend Health

Use continuously during all four scripts.

Metrics:

- `/health` status and response time
- `/ready` status and response time
- `/compliance/evaluate` status and response time
- pod readiness
- pod restart count
- recent warning/error events

Health loop:

```bash
while true; do
  date -Is
  kubectl -n synthetic-enterprise get pods -l app=compliance-service
  curl -sS -o /tmp/phase2-health.json -w "health_time=%{time_total}s http=%{http_code}\n" http://<target>/health
  curl -sS -o /tmp/phase2-ready.json -w "ready_time=%{time_total}s http=%{http_code}\n" http://<target>/ready
  curl -sS -o /tmp/phase2-evaluate.json -w "evaluate_time=%{time_total}s http=%{http_code}\n" \
    -X POST http://<target>/compliance/evaluate \
    -H "Content-Type: application/json" \
    -d '{"agent_id":"monitor","project_id":"phase2","capability":"policy_evaluation"}'
  sleep 60
done
```

Alert thresholds:

- health HTTP not `200`: escalate immediately
- ready HTTP not `200`: warn on first failure, escalate if two consecutive failures
- evaluate HTTP not `200`: stop current test and inspect logs
- any pod not `Running`: warn
- any restart count increase: stop clean-run evidence and investigate

Log commands:

```bash
kubectl -n synthetic-enterprise logs deployment/compliance-service --tail=200
kubectl -n synthetic-enterprise describe deployment compliance-service
kubectl -n synthetic-enterprise describe pods -l app=compliance-service
```

Validation gate:

```bash
jq -e '.status == "ok"' /tmp/phase2-health.json
jq -e '.status == "ready"' /tmp/phase2-ready.json
jq -e 'has("allowed") and has("reason") and has("policy_version")' /tmp/phase2-evaluate.json
```

## Dashboard 3: ZAP Scan Watch

Use during `run_zap_baseline.ps1`.

Metrics:

- scan process still running
- target reachable
- current report file size
- fail/warn counts in log

Commands:

```bash
watch -n 15 'tail -60 /tmp/phase2-zap.log | grep -E "FAIL-NEW|WARN-NEW|PASS:|Automation|error|ERROR"'
ls -lh scripts/testing/zap-baseline-report.html
curl -sS -o /dev/null -w "target_http=%{http_code} target_time=%{time_total}s\n" http://<target>/health
```

Alert thresholds:

- ZAP no output for 15 minutes: warn
- ZAP no output for 30 minutes: stop and inspect
- any critical/high finding: stop Phase 2 and escalate to security
- target unreachable: escalate to Ops

Validation gate:

```bash
grep -E "FAIL-NEW:" /tmp/phase2-zap.log
```

If no `FAIL-NEW` line exists, the scan did not produce a usable summary.

## Dashboard 4: DR Checkpoint Watch

Use during `dr_restore_check.ps1`.

Metrics:

- namespace exists
- deployment health
- service/endpoints present
- restore evidence availability
- audit-chain verification status

Commands:

```bash
kubectl get namespace synthetic-enterprise
kubectl -n synthetic-enterprise get deploy,pods,svc,endpoints
scripts/mock-vault-for-dr-test.sh audit-check | tee /tmp/phase2-vault-audit-check.json
```

Alert thresholds:

- namespace missing: stop and escalate
- endpoints empty: rollback or restore manifests
- audit-chain check fails: escalate to compliance owner
- RPO/RTO evidence missing: mark DR conditional, not pass

Validation gate:

```bash
jq -e '.audit_chain_valid == true' /tmp/phase2-vault-audit-check.json
```

## Dashboard 5: Blue-Green Watch

Use during `blue_green_validate.ps1`.

Metrics:

- active color
- candidate color
- deployment readiness
- endpoint count
- pod distribution
- rollback command availability

Commands:

```bash
kubectl -n synthetic-enterprise get deployment -l app=compliance-service
kubectl -n synthetic-enterprise rollout status deployment/compliance-service
kubectl -n synthetic-enterprise get endpoints compliance-service
kubectl -n synthetic-enterprise get pods -l app=compliance-service -o wide
```

Alert thresholds:

- deployment not fully ready: stop
- endpoints missing: rollback
- pods concentrated on a single failing node: warn and inspect scheduling
- rollback command absent from output: evidence incomplete

Validation gate:

```bash
kubectl -n synthetic-enterprise rollout status deployment/compliance-service --timeout=120s
```

## Dashboard 6: Decision Tree State

Use during the 24h ops SLA and Phase 2 window.

Metrics:

- SLA start timestamp
- elapsed time
- time remaining
- ops response state
- decision tree branch

Command:

```bash
SLA_START_EPOCH=<epoch-from-escalation-send>
while true; do
  now=$(date +%s)
  elapsed=$((now - SLA_START_EPOCH))
  remaining=$((86400 - elapsed))
  printf "elapsed=%02dh:%02dm remaining=%02dh:%02dm\n" \
    $((elapsed/3600)) $(((elapsed%3600)/60)) \
    $((remaining/3600)) $(((remaining%3600)/60))
  sleep 300
done
```

Alerts:

- T+23h: ops reply due within one hour
- T+24h with no response: escalate to program leadership
- ops response ambiguous: request clarification once, then escalate if unresolved

## Monitoring Failure Handling

If monitoring itself fails:

1. Stop claiming live metrics.
2. Capture raw script logs.
3. Verify target manually with curl and kubectl.
4. Restart the monitor.
5. Continue only if evidence gap is documented.

Escalate monitoring failure to ChatGPT execution owner if it cannot be recovered within 10 minutes.

