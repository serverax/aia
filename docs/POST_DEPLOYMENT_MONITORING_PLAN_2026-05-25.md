# Post-Deployment Monitoring and Support Plan (2026-05-25)

## Objective

Provide a concrete monitoring and support procedure for the first 48 hours after deployment.

## Monitoring Window

- **Hypercare start:** immediately after production cutover
- **Hypercare duration:** 48 hours
- **High-frequency checks:** first 2 hours

## Check Cadence

### 0-30 minutes

- Every 5 minutes:
  - deployment/pod readiness
  - endpoint availability
  - error rate
  - p95 latency
  - restart count

### 30-120 minutes

- Every 15 minutes:
  - same checks as above
  - ingress/canary annotation correctness
  - warning events in namespace

### 2-48 hours

- Hourly:
  - service health and SLO trend
  - audit event flow
  - policy/admission anomalies

## Minimum Commands

```bash
kubectl -n ordinox-ai get deploy,svc,pods
kubectl -n ordinox-ai get endpoints -o wide
kubectl -n ordinox-ai get events --sort-by='.lastTimestamp' | tail -20
kubectl -n ordinox-ai get ingress compliance-service-green-canary -o jsonpath='{.metadata.annotations.nginx\.ingress\.kubernetes\.io/canary-weight}'
```

## Alert Thresholds

- **Rollback immediately** if:
  - error rate > 10% for two consecutive windows
  - sustained p95 latency beyond agreed SLO threshold
  - repeated readiness failures or crash loops
  - ingress split state diverges from intended rollout step
  - compliance response contract or audit logging breaks

## Support Roles

- **Deployment lead:** executes rollout/rollback and captures evidence
- **Engineering on-call:** triage and hotfix support
- **Security/compliance reviewer:** validates policy and audit path integrity

## Incident Handling

1. Detect and confirm anomaly.
2. Pause promotion.
3. Apply rollback checklist if thresholds are hit.
4. Record timeline, commands, and evidence in incident log.
5. Provide stakeholder update every 15 minutes until stable.

## Feedback Loop

- Capture user/stakeholder feedback in first 24 hours.
- Classify into:
  - urgent defect
  - performance tuning
  - UX/documentation improvement
- Convert actionable items into tracked backlog tickets.
