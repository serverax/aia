# Rollback Checklist

Use this checklist during staging/production deploy windows whenever rollout health degrades.

## 1) Trigger Conditions

Rollback immediately if any of the following is true:

- Canary weight update fails or ingress annotation does not reconcile.
- Error rate exceeds threshold for two consecutive windows.
- Latency SLO breach persists after one mitigation cycle.
- Pods enter `CrashLoopBackOff`, `ImagePullBackOff`, or fail readiness.
- Compliance endpoint contract breaks (missing required response fields).
- Audit logging path fails.

## 2) Immediate Stabilization

1. Freeze promotions (do not increase traffic weight).
2. Set canary weight to `0` on green ingress.
3. Notify deployment bridge and incident owner.

Command:

```bash
NAMESPACE=ordinox-ai INGRESS=compliance-service-green-canary scripts/compliance/rollback-blue-green.sh
```

## 3) Roll Back Workload Revision

- Undo deployment revision for the affected compliance service.
- Wait for rollout to complete.
- Verify blue endpoints are healthy.

Fallback command path:

```bash
KUBECONFIG=<path> NAMESPACE=ordinox-ai DEPLOYMENT=compliance-service scripts/rollback-to-blue.sh
```

## 4) Verify Recovery

Run all before declaring rollback complete:

- `kubectl -n ordinox-ai get deploy,rs,pods`
- `kubectl -n ordinox-ai get endpoints compliance-service-blue compliance-service-green -o wide`
- Validate health endpoint and one representative functional request.
- Confirm logs are stable and error rate returns to baseline.

## 5) Data and Policy Safety

- Confirm no schema migration partially failed.
- Confirm admission/network policies are unchanged (unless rollback explicitly includes security layer changes).
- Run RBAC drift check if deployment touched service accounts/roles.

## 6) Communication and Documentation

- Record rollback timestamp and trigger in incident/release notes.
- Attach command output and cluster events to ticket.
- Note whether rollback is temporary or final.

## 7) Exit Criteria

Rollback is considered complete only when:

- Service is stable at known-good version.
- SLO/SLI metrics return to acceptable baseline.
- No active rollout actions remain.
- Deployment lead and incident owner both sign off.
