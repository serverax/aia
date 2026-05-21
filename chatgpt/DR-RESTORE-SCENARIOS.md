# DR Restore Scenarios

## Purpose

This document defines Sprint 8 disaster recovery scenarios for `compliance-service` and its supporting compliance data. It specifies what must be backed up, recovery targets, restore validation, and evidence required for sign-off.

## RTO/RPO Targets

| Target | Requirement |
| --- | --- |
| RTO | 60 minutes maximum from incident declaration to restored service |
| RPO | 15 minutes maximum data loss for compliance/audit data |
| Service availability after restore | `compliance-service` deployment `2/2` ready |
| Validation | `/health`, `/ready`, and `/compliance/evaluate` return HTTP 200 with valid JSON |

If either RTO or RPO is missed, DR validation is incomplete and must be escalated.

## What Gets Backed Up

### Kubernetes Manifests

Back up or version-control:

- `infrastructure/compliance/compliance-service.yaml`
- `infrastructure/compliance/network-policy.yaml`
- `infrastructure/compliance/ingress.yaml`
- `infrastructure/compliance/audit-policy.sql`
- Sprint 8 testing scripts under `scripts/testing/`

Restore method:

```bash
kubectl apply -f infrastructure/compliance/
```

### Kubernetes Secrets

Back up out-of-band, not in Git:

- `synthetic-enterprise/llm-api-keys`
- future GHCR `imagePullSecret`
- future Vault app tokens

Restore method:

```bash
kubectl -n synthetic-enterprise create secret generic llm-api-keys \
  --from-literal=ANTHROPIC_API_KEY=<restored-value>
```

For real production, secrets should be restored from Vault, SealedSecrets, External Secrets, or the approved secret manager.

### Compliance Policy State

Back up:

- kill-switch state
- disabled agents/projects/capabilities
- policy version metadata
- human override records

Current placeholder runtime stores no durable policy state. Production runtime must persist this state before full DR sign-off.

### Audit Logs

Back up:

- compliance audit table
- hash-chain fields: `previous_hash`, `audit_hash`
- timestamps, actor IDs, event types, decisions, payloads

Restore method:

- restore PostgreSQL backup
- run audit hash-chain verification
- compare latest restored event timestamp against RPO target

### Runtime Evidence

Capture before and after restore:

```bash
kubectl -n synthetic-enterprise get deploy,pods,svc,endpoints
kubectl -n synthetic-enterprise get events --sort-by=.lastTimestamp
kubectl -n synthetic-enterprise rollout history deployment/compliance-service
```

## Restore Verification Steps

A restore is successful only when all are true:

1. Namespace exists:

```bash
kubectl get namespace synthetic-enterprise
```

2. Deployment is healthy:

```bash
kubectl -n synthetic-enterprise get deployment compliance-service
kubectl -n synthetic-enterprise rollout status deployment/compliance-service
```

Expected:

```text
compliance-service   2/2   2   2
deployment "compliance-service" successfully rolled out
```

3. Endpoints are populated:

```bash
kubectl -n synthetic-enterprise get endpoints compliance-service
```

Expected:

```text
compliance-service   <pod-ip>:8000,<pod-ip>:8000
```

4. API responds:

```bash
curl -fsS http://<target>/health
curl -fsS http://<target>/ready
curl -fsS -X POST http://<target>/compliance/evaluate \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"compliance_officer_v1_20250520","project_id":"dr-check","capability":"policy_evaluation"}'
```

Expected:

```json
{"status":"ok"}
{"status":"ready"}
{"allowed":true,"reason":"allowed","policy_version":"..."}
```

5. Audit verification passes:

```text
audit_chain_valid=true
latest_restored_event_age <= 15 minutes
```

Current placeholder runtime cannot fully satisfy audit verification. Mark this as a production follow-up until durable audit storage is wired.

## Scenario 1: Compliance Pod Failure

Trigger:

- One or more `compliance-service` pods crash, are evicted, or enter `ImagePullBackOff`.

Detection:

```bash
kubectl -n synthetic-enterprise get pods -l app=compliance-service
kubectl -n synthetic-enterprise get events --sort-by=.lastTimestamp
```

Recovery:

1. Inspect events and logs:

```bash
kubectl -n synthetic-enterprise describe pod <pod>
kubectl -n synthetic-enterprise logs <pod>
```

2. Restart deployment:

```bash
kubectl -n synthetic-enterprise rollout restart deployment/compliance-service
kubectl -n synthetic-enterprise rollout status deployment/compliance-service
```

3. If restart fails, roll back:

```bash
kubectl rollout undo deployment/compliance-service -n synthetic-enterprise
kubectl -n synthetic-enterprise rollout status deployment/compliance-service
```

Pass criteria:

- deployment returns to `2/2`
- endpoints repopulate
- health/ready/evaluate pass

Escalate if:

- repeated crashes continue after rollback
- image pull fails because registry auth is missing
- PodSecurity blocks pod creation

## Scenario 2: Namespace Corruption Or Resource Deletion

Trigger:

- `synthetic-enterprise` resources are accidentally deleted or corrupted.

Detection:

```bash
kubectl get namespace synthetic-enterprise
kubectl -n synthetic-enterprise get all
```

Recovery:

1. Recreate namespace if missing:

```bash
kubectl create namespace synthetic-enterprise
```

2. Restore secrets from approved secret source:

```bash
kubectl -n synthetic-enterprise create secret generic llm-api-keys \
  --from-literal=ANTHROPIC_API_KEY=<restored-value>
```

3. Reapply manifests:

```bash
kubectl apply -f infrastructure/compliance/
```

4. Verify rollout:

```bash
kubectl -n synthetic-enterprise rollout status deployment/compliance-service
kubectl -n synthetic-enterprise get endpoints compliance-service
```

Pass criteria:

- all required resources restored
- compliance endpoints pass
- NetworkPolicy and Ingress exist if required for the environment

Escalate if:

- secret source is unavailable
- manifests no longer match the expected release
- restore exceeds 60-minute RTO

## Scenario 3: Audit Database Loss Or Corruption

Trigger:

- PostgreSQL audit table is lost, corrupted, or restored from backup.

Detection:

- audit-chain verification fails
- database unavailable
- latest audit event timestamp exceeds RPO

Recovery:

1. Freeze external-send capability through compliance policy if available.
2. Restore PostgreSQL from the latest verified backup.
3. Run migrations if schema is missing:

```bash
psql < infrastructure/compliance/audit-policy.sql
```

4. Run audit hash-chain verification.
5. Compare restored timestamp against RPO.
6. Resume compliance writes only after verification passes or human override is recorded.

Pass criteria:

- database reachable
- audit table present
- audit hash chain verifies
- restored data is within 15-minute RPO

Escalate if:

- hash chain fails
- backup is older than RPO
- manual override is required to resume service

## Evidence Checklist

Capture and attach:

- [ ] incident start time
- [ ] restore start time
- [ ] restore finish time
- [ ] measured RTO
- [ ] latest restored audit event timestamp
- [ ] measured RPO
- [ ] `kubectl get deploy,pods,svc,endpoints -n synthetic-enterprise`
- [ ] `kubectl get events -n synthetic-enterprise --sort-by=.lastTimestamp`
- [ ] health/ready/evaluate JSON responses
- [ ] backup identifier
- [ ] restore command output
- [ ] audit-chain verification output
- [ ] rollback command used, if any
- [ ] human approval or override, if any

## DR Result Template

```text
DR Scenario:
Start time:
Finish time:
Measured RTO:
Measured RPO:
Resources restored:
Audit chain valid:
Endpoint validation:
Rollback used:
Human override:
Final status: PASS | FAIL | CONDITIONAL
Notes:
```

## Current Limitations

- Placeholder compliance runtime has no durable policy state.
- Placeholder `llm-api-keys` secret must be replaced with the real key.
- Vault is not deployed yet.
- Full audit-chain DR cannot pass until durable audit storage is connected.

These limitations do not block documenting DR procedures, but they must be resolved before final production DR sign-off.
