# Sprint 8 Execution Plan: Load, Security, DR, Blue-Green

## 1. Script Execution Sequence

Run these scripts in order after the authoritative Talos kubeconfig is verified.

| Order | Script | Purpose | What It Tests | Expected Duration |
| --- | --- | --- | --- | --- |
| 1 | `scripts/testing/run_load_test.ps1` | Validate runtime capacity and latency | `/health`, `/ready`, `/compliance/evaluate` under concurrent users | 30 minutes default; 10 seconds for smoke sample |
| 2 | `scripts/testing/run_zap_baseline.ps1` | Run OWASP ZAP baseline security scan | HTTP headers, passive disclosure checks, common baseline web risks | 2-10 minutes |
| 3 | `scripts/testing/dr_restore_check.ps1` | Capture DR checkpoint state | Pods, deployments, services, restore evidence requirements | 1-3 minutes plus manual restore evidence |
| 4 | `scripts/testing/blue_green_validate.ps1` | Validate release and rollback posture | Rollout health, endpoints, pod state, active/candidate colors, rollback command | 1-3 minutes |

## 2. Pre-Flight Checklist

Before running any Sprint 8 script:

- [ ] Talos kubeconfig is present and exported.
- [ ] `kubectl config current-context` returns the expected Talos context.
- [ ] `kubectl get nodes -o wide` shows the Talos nodes as `Ready`.
- [ ] `talosctl version` succeeds with no CA/auth error.
- [ ] `compliance-service` is running `2/2` replicas.
- [ ] `ingress-nginx` is operational if testing through ingress.
- [ ] Orchestrator mock data is seeded if workflows beyond compliance endpoints are tested.
- [ ] Previous failed test Jobs or port-forwards are cleaned up.

## 3. Per-Script Details

### A. `run_load_test.ps1`

Purpose: Validate service latency, throughput, and error rate under synthetic load.

Command:

```powershell
pwsh scripts/testing/run_load_test.ps1 `
  -HostUrl <target-url> `
  -Users 1000 `
  -SpawnRate 50 `
  -RunTime 30m `
  -Docker
```

Success criteria:

- Error rate below `0.1%`.
- `/health` and `/ready` p95 latency below `500 ms`.
- `/compliance/evaluate` p95 latency below `1,500 ms`.
- No pod restarts or `CrashLoopBackOff` during the run.
- HTML report generated.

Example good output:

```text
GET /health                    0(0.00%) failures
GET /ready                     0(0.00%) failures
POST /compliance/evaluate      0(0.00%) failures
Aggregated p95                 below SLA threshold
```

Example bad output:

```text
OSError(101, 'Network is unreachable')
HTTPError('500 Server Error')
Aggregated failures > 0.1%
```

How to read results:

- Check total requests and total failures first.
- Check p95 per endpoint, not just aggregate average.
- Check Kubernetes events for pod restarts during the same time window.

Failure handling:

- Docker cannot reach target: rerun as an in-cluster Kubernetes Job.
- High latency: inspect pod CPU/memory, node pressure, and service endpoint distribution.
- HTTP 5xx: inspect compliance-service logs first, then ingress logs if traffic went through ingress.
- Pod restarts: stop test and inspect `kubectl describe pod`.

Rollback:

- Load testing should not mutate service state.
- If load causes instability, scale down test Job/process and roll back the app:

```bash
kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
```

Escalate if p95 exceeds SLA after one clean rerun or if any pod restarts repeatedly.

### B. `run_zap_baseline.ps1`

Purpose: Run a baseline OWASP ZAP passive scan.

Command:

```powershell
pwsh scripts/testing/run_zap_baseline.ps1 `
  -TargetUrl <target-url> `
  -ReportPath scripts/testing/zap-baseline-report.html
```

Success criteria:

- `FAIL-NEW: 0`.
- No critical or high findings.
- Informational warnings are documented with Sprint 9 follow-up tickets.

Example good output:

```text
FAIL-NEW: 0
WARN-NEW: 2
PASS: 65
```

Example bad output:

```text
FAIL-NEW: 1
Cross Site Scripting
Authentication Request Identified with unexpected exposure
```

How to read results:

- `FAIL-NEW` blocks release unless security signs off.
- `WARN-NEW` must be reviewed and either fixed or explicitly deferred.
- Confirm the scan target is the correct Talos endpoint, not local/AKS.

Failure handling:

- Docker credential/image error: use configurable `-Image` or run ZAP in-cluster.
- Target unreachable: verify ingress/service endpoint first.
- Critical finding: stop release validation and escalate to security.

Rollback:

- ZAP is read-only baseline scanning.
- If scan reveals an exploitable issue, roll back service or disable ingress exposure:

```bash
kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
```

Escalate critical/high findings to the security team immediately.

### C. `dr_restore_check.ps1`

Purpose: Capture disaster recovery checkpoint evidence and runtime state.

Command:

```powershell
pwsh scripts/testing/dr_restore_check.ps1 `
  -WslKubeconfig <path-to-talos-kubeconfig>
```

Success criteria:

- Required pods, deployments, and services are visible.
- Restore evidence is attached separately.
- RTO and RPO are measured and recorded.
- Audit-chain verification evidence is attached.

Example good output:

```text
NAME                                  READY   STATUS
compliance-service-...                1/1     Running
deployment.apps/compliance-service    2/2
service/compliance-service            8000/TCP
DR checkpoint collected.
```

Example bad output:

```text
Error from server (NotFound): namespaces "synthetic-enterprise" not found
No resources found
kubectl failed
```

How to read results:

- This script is a checkpoint, not a full restore by itself.
- It must be paired with backup logs, restore logs, RTO/RPO measurements, and audit-chain verification.

Failure handling:

- Wrong context: stop and correct kubeconfig.
- Missing resources: restore manifests before continuing.
- Missing backup evidence: mark DR incomplete and escalate.

Rollback:

- If DR validation damages runtime state, restore from the last known-good manifests and run:

```bash
kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
```

Escalate failed restore or missing backup evidence to backup/infrastructure owners.

### D. `blue_green_validate.ps1`

Purpose: Validate release health, endpoint availability, and rollback readiness.

Command:

```powershell
pwsh scripts/testing/blue_green_validate.ps1 `
  -WslKubeconfig <path-to-talos-kubeconfig> `
  -ActiveColor blue `
  -CandidateColor green
```

Success criteria:

- Deployment shows full readiness.
- Rollout status succeeds.
- Endpoints are populated.
- Pods are running.
- Rollback command is printed.

Example good output:

```text
compliance-service   2/2   2   2
deployment "compliance-service" successfully rolled out
compliance-service   10.244.x.x:8000,10.244.y.y:8000
Blue-green validation checkpoint complete.
Rollback command: kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
```

Example bad output:

```text
deployment "compliance-service" exceeded its progress deadline
ENDPOINTS <none>
kubectl failed
```

How to read results:

- `2/2` ready and populated endpoints are required.
- Pod listing must show `Running` and no repeated restarts.
- Rollback command must match the deployed app and namespace.

Failure handling:

- Rollout timeout: inspect events and container logs.
- No endpoints: check service selector and pod labels.
- Wrong context: stop and correct kubeconfig.

Rollback:

```bash
kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
kubectl -n synthetic-enterprise rollout status deployment/compliance-service
```

Escalate if rollback fails or endpoints remain empty after rollback.

## 4. Report Output Locations

Expected result artifacts:

- Load test report: `scripts/testing/load-test-report.html`
- ZAP report: `scripts/testing/zap-baseline-report.html`
- DR checkpoint: `scripts/testing/dr-restore-evidence.json`
- Blue-green evidence: `scripts/testing/blue-green-validation.json`

Current scripts print primary evidence to console. If JSON evidence files are required, capture output with:

```powershell
pwsh scripts/testing/dr_restore_check.ps1 *> scripts/testing/dr-restore-evidence.txt
pwsh scripts/testing/blue_green_validate.ps1 *> scripts/testing/blue-green-validation.txt
```

## 5. Success Summary Template

Use this format after all four scripts complete:

```text
Sprint 8 Execution Summary

✅ Load Test:
- p50:
- p95:
- p99:
- throughput:
- errors:
- report:

✅ ZAP Baseline:
- total checks:
- vulnerabilities found:
- severity breakdown:
- warnings deferred:
- report:
- PASS/FAIL:

✅ DR Restore:
- resources checked:
- backup evidence:
- restore evidence:
- RTO:
- RPO:
- validation passed:

✅ Blue-Green:
- active color:
- candidate color:
- canary health:
- endpoints:
- rollback ready:
- rollback command:
```

## 6. Escalation Matrix

| Failure | First Check | Recovery | Escalate To |
| --- | --- | --- | --- |
| Load test timeout | compliance-service logs and pod events | Reduce load, rerun, inspect resources | Orchestrator/platform owner if upstream workflow fails |
| Load test high p95 | CPU/memory, node pressure, endpoint spread | Scale replicas or tune resources | Platform owner |
| ZAP critical/high finding | ZAP report details | Stop release, patch issue | Security team |
| ZAP target unreachable | ingress/service reachability | Run in-cluster or fix ingress | Ops |
| DR restore fails | backup logs and restore command output | Restore from previous backup or manifests | Backup/infrastructure owner |
| Missing audit-chain evidence | audit verifier output | Re-run verifier or pause release | Compliance owner |
| Blue-green rollout fails | `kubectl describe deployment`, events | `kubectl rollout undo` | Cluster diagnostics / platform owner |
| Empty service endpoints | selector/label mismatch | fix labels or service selector | Platform owner |
| Wrong kube context | `kubectl config current-context` | stop and switch kubeconfig | Infrastructure owner |
