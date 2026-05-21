# PHASE 2 ROLLBACK DECISION MATRIX

## Purpose

This matrix defines when Phase 2 continues, pauses, escalates, or rolls back. It covers all four scripts: load test, ZAP baseline, DR checkpoint, and blue-green validation.

## Global Rules

- Do not roll back for a tool failure that did not mutate production.
- Roll back immediately if the active deployment becomes unhealthy.
- Escalate critical/high security findings to security before any production decision.
- Escalate wrong cluster context to Ops immediately.
- Capture evidence before and after rollback.

Global rollback command:

```bash
kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
kubectl -n synthetic-enterprise rollout status deployment/compliance-service
```

Global evidence command:

```bash
scripts/capture-all-evidence.sh <run-id> > /tmp/phase2-rollback-evidence.json
```

## Script 1: run_load_test.ps1

### Scenario A: Load test passes

Conditions:

- p95 health/readiness `< 500 ms`
- p95 evaluate `< 1,500 ms`
- error rate `< 0.1%`
- no pod restarts

Status: PASS

Action:

```text
Proceed to Script 2: run_zap_baseline.ps1
```

Rollback: not needed.

### Scenario B: Load test slow but not failed

Conditions:

- p95 `> 3s` but `< 5s`
- error rate below `1%`
- no pod restarts

Status: WARNING

Investigation:

```bash
kubectl top nodes
kubectl top pods -n synthetic-enterprise --containers
kubectl -n synthetic-enterprise logs deployment/compliance-service --tail=300
kubectl -n synthetic-enterprise get events --sort-by=.lastTimestamp | tail -30
```

Decision:

- If CPU or memory pressure is high: hold, escalate to Ops, rerun after resources are stable.
- If backend logs show slow requests: escalate to Gemini/backend owner.
- If metrics normalize within 10 minutes: proceed with warning logged.

Rollback:

- Only rollback if new application code was deployed immediately before the test.
- Otherwise continue after documenting warning.

### Scenario C: Load test fails

Conditions:

- p95 `> 5s`
- error rate `> 10%`
- sustained 5xx responses
- pod restarts

Status: FAIL

Investigation:

```bash
scripts/capture-all-evidence.sh phase2-load-fail > /tmp/phase2-load-fail-evidence.json
kubectl -n synthetic-enterprise describe pods -l app=compliance-service
kubectl -n synthetic-enterprise logs deployment/compliance-service --tail=500
kubectl get nodes -o wide
```

Decision:

- Backend pod crash: escalate to Gemini if code path involved; Ops if scheduling/resource issue.
- Node pressure: escalate to Ops.
- Network errors: escalate to Ops with event logs.

Rollback:

```bash
kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
```

Continue only after rerun passes.

### Scenario D: Load test hangs

Conditions:

- no output for 15 minutes
- process exists but no request count increases

Status: HANG

Action:

```bash
pgrep -af run_load_test.ps1
tail -100 /tmp/phase2-load-test.log
pkill -f run_load_test.ps1
```

Escalation:

- ChatGPT execution owner if script issue.
- Ops if target unreachable or DNS/ingress fails.

Rollback: not applicable unless service became unhealthy.

## Script 2: run_zap_baseline.ps1

### Scenario A: No critical or high findings

Conditions:

- `FAIL-NEW: 0`
- no critical/high findings
- warnings documented

Status: PASS

Action: proceed to DR checkpoint.

Rollback: not needed.

### Scenario B: Critical finding

Conditions:

- any critical vulnerability
- exposed secret/token/client data
- unauthenticated mutation of compliance state

Status: FAIL

Investigation:

```bash
grep -E "FAIL-NEW|CRITICAL|HIGH" /tmp/phase2-zap.log
cp scripts/testing/zap-baseline-report.html /tmp/phase2-zap-critical-report.html
```

Decision:

- Stop Phase 2.
- Escalate to security and Claude Code.
- Do not proceed without written risk acceptance or hotfix.

Rollback:

```bash
kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
```

### Scenario C: High finding with possible false positive

Conditions:

- high finding appears
- impact unclear

Status: CONDITIONAL

Investigation:

```bash
grep -A5 -B5 "HIGH" /tmp/phase2-zap.log
curl -i <affected-url>
```

Decision:

- Security owner must classify as false positive or blocker.
- If false positive: document rule ID, URL, rationale, owner.
- If real: stop and fix.

Rollback: only if exposure is active and exploitable.

### Scenario D: ZAP crashes or target unreachable

Conditions:

- container exits before summary
- no `FAIL-NEW` line
- target connection refused

Status: ERROR

Investigation:

```bash
tail -100 /tmp/phase2-zap.log
curl -sS -i <target-url>/health
kubectl -n synthetic-enterprise get svc,endpoints
```

Decision:

- Tool/runtime issue: rerun in-cluster.
- Target issue: escalate to Ops.

Rollback: not applicable unless service health is degraded.

## Script 3: dr_restore_check.ps1

### Scenario A: DR checkpoint passes

Conditions:

- pods listed
- deployments listed
- services listed
- restore evidence attached or limitation documented

Status: PASS or CONDITIONAL

Action:

```text
Proceed to blue-green validation.
```

Rollback: not needed.

### Scenario B: Namespace missing

Conditions:

- `synthetic-enterprise` namespace not found

Status: FAIL

Investigation:

```bash
kubectl get ns
kubectl get events -A --sort-by=.lastTimestamp | tail -50
```

Decision:

- If accidental deletion: restore namespace and manifests.
- If wrong context: stop and escalate to Ops.

Rollback:

```bash
kubectl apply -f infrastructure/compliance/
```

Escalate if namespace restoration exceeds 60 minutes.

### Scenario C: Audit-chain evidence missing

Conditions:

- audit verification cannot run
- durable audit storage not connected

Status: CONDITIONAL

Investigation:

```bash
ls infrastructure/compliance/audit-policy.sql
scripts/mock-vault-for-dr-test.sh audit-check
```

Decision:

- Document limitation if placeholder runtime is in use.
- Require production follow-up before full DR sign-off.

Rollback: not applicable.

### Scenario D: Restore exceeds RTO/RPO

Conditions:

- RTO `> 60 min`
- RPO `> 15 min`

Status: FAIL

Investigation:

```bash
grep -E "Start time|Finish time|Measured RTO|Measured RPO" /tmp/phase2-dr.log
```

Decision:

- Escalate to backup/infrastructure owner.
- Do not mark DR pass.

Rollback: restore previous known-good state if service is degraded.

## Script 4: blue_green_validate.ps1

### Scenario A: Blue-green validation passes

Conditions:

- deployment fully ready
- rollout status succeeds
- endpoints populated
- pods running
- rollback command printed

Status: PASS

Action:

```text
Proceed to Phase 2 final report.
```

Rollback: not needed.

### Scenario B: Rollout timeout

Conditions:

- rollout status exceeds timeout
- deployment not available

Status: FAIL

Investigation:

```bash
kubectl -n synthetic-enterprise describe deployment compliance-service
kubectl -n synthetic-enterprise get events --sort-by=.lastTimestamp | tail -50
kubectl -n synthetic-enterprise get pods -l app=compliance-service -o wide
```

Decision:

- Image pull error: fix imagePullSecret or revert image.
- PodSecurity error: fix securityContext or revert.
- Readiness failure: inspect app logs.

Rollback:

```bash
kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
kubectl -n synthetic-enterprise rollout status deployment/compliance-service
```

### Scenario C: Endpoints empty

Conditions:

- service exists
- pods exist
- endpoints empty

Status: FAIL

Investigation:

```bash
kubectl -n synthetic-enterprise get svc compliance-service -o yaml
kubectl -n synthetic-enterprise get pods --show-labels
```

Decision:

- If selector mismatch: fix labels/selectors.
- If pods not ready: inspect readiness probe and app logs.

Rollback:

```bash
kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
```

### Scenario D: Rollback fails

Conditions:

- `kubectl rollout undo` fails
- rollout remains unavailable after undo

Status: CRITICAL

Investigation:

```bash
kubectl -n synthetic-enterprise rollout history deployment/compliance-service
kubectl -n synthetic-enterprise describe deployment compliance-service
kubectl -n synthetic-enterprise get events --sort-by=.lastTimestamp | tail -100
```

Decision:

- Escalate to Ops immediately.
- Freeze further Phase 2 activity.
- Restore manifests from Git if rollout history cannot recover.

## Overall Phase 2 Decision

| Outcome | Action |
| --- | --- |
| All four scripts pass | Proceed to Phase 3/Cursor regression and production sign-off |
| One script warning, no critical impact | Document warning and continue if owner accepts |
| One script fails and hotfix is possible within 30 min | Hotfix, rerun failed script, continue if pass |
| One script fails and no 30-min fix exists | Escalate to program leadership; delay production |
| Wrong cluster context | Stop immediately; invalidate evidence |
| Rollback fails | Critical incident; Ops owns recovery |

## Escalation Owners

| Area | Owner |
| --- | --- |
| Talos credentials/context | Ops infrastructure |
| Node pressure, ingress, DNS, image pulls | Ops infrastructure |
| Compliance service app behavior | ChatGPT lane |
| Gemini backend latency/errors | Gemini lane |
| Security critical/high findings | Security / Claude Code |
| Frontend regression failures | Cursor lane |
| Production delay decision | Program leadership |

