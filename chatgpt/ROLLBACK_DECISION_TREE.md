# Rollback Decision Tree

## Immediate Rollback Triggers

Run rollback immediately when any of these occur during Sprint 8 execution:

- `compliance-service` rollout fails or times out.
- Service endpoints are empty after rollout.
- Any pod enters repeated `CrashLoopBackOff`.
- Load test causes sustained `5xx` responses.
- ZAP identifies a critical/high exploitable issue that requires removing exposure.
- DR restore leaves service in a partial or unknown state.

## Rollback Command

```bash
export KUBECONFIG=<talos-kubeconfig>
scripts/rollback-to-blue.sh
```

Direct command:

```bash
kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
kubectl -n synthetic-enterprise rollout status deployment/compliance-service
```

## Decision Tree

1. Did the failure mutate production resources?
   - No: stop the test, capture logs, do not roll back.
   - Yes: continue.

2. Is the active deployment unhealthy?
   - Yes: run rollback.
   - No: pause traffic/canary and inspect.

3. Are endpoints empty?
   - Yes: run rollback and inspect service selectors.
   - No: inspect application logs first.

4. Did rollback succeed?
   - Yes: capture evidence and report conditional/fail.
   - No: escalate to platform owner immediately.

## Post-Rollback Evidence

Capture:

- rollout undo output
- rollout status output
- pod list
- endpoints list
- events from the namespace
- health/ready/evaluate response payloads

## What Not To Roll Back

Do not delete:

- namespace
- secrets
- audit log storage
- unrelated Gemini/Cursor/Claude Code workloads

Unless explicitly directed, rollback only the affected deployment.

