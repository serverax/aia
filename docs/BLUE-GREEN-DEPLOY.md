# Blue-Green Compliance Deployment

This runbook defines the Sprint 10 blue-green deployment flow for the
`compliance-service` in the `ordinox-ai` namespace. It assumes Flux owns the
base deployment and ChatGPT-owned scripts only operate after the base rollout
gate is green.

## Sequence

1. Confirm Flux has reconciled the base `compliance-service`.
2. Run the rollout gate.
3. Apply the blue-green traffic split configuration.
4. Ramp traffic from blue to green.
5. Monitor latency, errors, pod restarts, and security findings.
6. Roll back immediately on any hard trigger.

## Prerequisites

- Claude Code namespace rename commit has landed.
- Flux has reconciled `ordinox-ai`.
- `kubectl config current-context` returns `admin@ordinox-talos-ha`.
- `compliance-service` exists in `ordinox-ai`.
- NGINX Ingress Controller is installed.
- `infrastructure/compliance/blue-green-traffic-split.yaml` is present.

## Gate 1: Base Rollout

Run:

```bash
NAMESPACE=ordinox-ai scripts/compliance/rollout-gate.sh
```

Pass criteria:

- deployment rollout succeeds within `120s`
- desired replicas are ready
- pods are `Running`
- no pod is in `CrashLoopBackOff`, `ImagePullBackOff`, `ErrImagePull`, or
  `CreateContainerError`
- `compliance-service` endpoint has at least one address

Evidence:

```text
reports/blue-green/rollout-context.txt
reports/blue-green/rollout-status.txt
reports/blue-green/rollout-resources.txt
reports/blue-green/base-endpoints.txt
```

If this gate fails, do not apply blue-green resources. Escalate to Ops for
cluster/resource issues or Gemini for backend rollout issues.

## Gate 2: Apply Blue-Green Config

Run:

```bash
scripts/compliance/apply-blue-green.sh
```

This applies:

- `Service/compliance-service-blue`
- `Service/compliance-service-green`
- `Ingress/compliance-service-blue`
- `Ingress/compliance-service-green-canary`
- `ConfigMap/compliance-blue-green-plan`

Pass criteria:

- server-side dry-run succeeds
- apply succeeds
- blue and green services exist
- blue and green endpoints are populated
- canary ingress annotation is live at `5`

Evidence:

```text
reports/blue-green/apply-context.txt
reports/blue-green/apply-dry-run.txt
reports/blue-green/apply-output.txt
reports/blue-green/apply-services.txt
reports/blue-green/apply-ingresses.txt
reports/blue-green/apply-endpoints.txt
reports/blue-green/canary-weight.txt
```

## Traffic Ramp

Target sequence:

```text
0% -> 5% -> 25% -> 50% -> 100%
```

For each weight:

1. Apply the ingress canary weight.
2. Wait 10 seconds for NGINX reconciliation.
3. Send 100 requests through the ingress.
4. Count blue vs green backend responses.
5. Validate observed green traffic is within `+/- 2%` of target.

Manual weight command:

```bash
kubectl -n ordinox-ai annotate ingress compliance-service-green-canary \
  nginx.ingress.kubernetes.io/canary-weight='25' --overwrite
```

Health checks:

```bash
kubectl -n ordinox-ai get endpoints compliance-service-blue compliance-service-green -o wide
kubectl -n ordinox-ai get pods -l app=compliance-service -o wide
kubectl -n ordinox-ai get ingress compliance-service-green-canary -o yaml
```

## Rollback Decision Tree

Rollback immediately if any of these occur:

- green endpoint missing
- green rollout times out
- p95 latency above `5000ms`
- error rate above `10%`
- critical or high ZAP finding
- audit logging failure
- `/compliance/evaluate` response misses `allowed`, `reason`, or
  `policy_version`
- pod restart during ramp

Run:

```bash
scripts/compliance/rollback-blue-green.sh
```

Dry-run:

```bash
DRY_RUN=true scripts/compliance/rollback-blue-green.sh
```

Rollback actions:

1. Set green canary weight to `0`.
2. Undo `deployment/compliance-service-green`.
3. Print blue and green endpoints.

## Troubleshooting

### Endpoint Not Ready

Commands:

```bash
kubectl -n ordinox-ai describe endpoints compliance-service-blue
kubectl -n ordinox-ai describe endpoints compliance-service-green
kubectl -n ordinox-ai get pods --show-labels
```

Likely causes:

- deployment labels do not match service selectors
- green deployment has not rolled out
- pod readiness probe is failing

### Weight Not Applying

Commands:

```bash
kubectl -n ordinox-ai get ingress compliance-service-green-canary -o yaml
kubectl -n ingress-nginx logs deployment/ingress-nginx-controller --tail=100
```

Likely causes:

- canary annotations rejected
- ingress class mismatch
- NGINX controller has not reconciled yet

### Traffic Not Shifting

Commands:

```bash
kubectl -n ordinox-ai get ingress -o wide
kubectl -n ordinox-ai get svc compliance-service-blue compliance-service-green -o wide
curl -s -H 'Host: ordinoxai.com' http://<ingress-ip>/compliance/evaluate
```

Likely causes:

- request path not routed through NGINX
- host header mismatch
- backends do not return color markers

### Security Finding During Ramp

Commands:

```bash
scripts/testing/run_zap_baseline.ps1 -TargetUrl http://<target>
scripts/compliance/rollback-blue-green.sh
```

Critical/high findings stop promotion. Claude Code/security owner decides hotfix
or release delay.

## Manual CLI Reference

Rollout gate:

```bash
scripts/compliance/rollout-gate.sh
```

Apply split:

```bash
scripts/compliance/apply-blue-green.sh
```

Set canary weight:

```bash
kubectl -n ordinox-ai annotate ingress compliance-service-green-canary \
  nginx.ingress.kubernetes.io/canary-weight='50' --overwrite
```

Rollback:

```bash
scripts/compliance/rollback-blue-green.sh
```

Evidence directory:

```text
reports/blue-green/
```
