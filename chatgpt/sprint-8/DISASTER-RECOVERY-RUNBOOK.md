# Disaster Recovery Runbook

## Objectives

- RTO: 60 minutes
- RPO: 15 minutes
- Compliance action: freeze external-send capability before recovery work starts

## Preconditions

- Human incident commander assigned
- Human compliance lead assigned
- Latest backup inventory available
- Kubernetes access verified
- Database restore credentials available

## Procedure

1. Activate containment.
   - Enable compliance kill switch for `external_send`.
   - Record actor, reason, timestamp, and source.

2. Snapshot current state.
   - Export pod status.
   - Export deployment revisions.
   - Export recent audit-chain verification status.

3. Restore databases.
   - Restore PostgreSQL from latest verified backup.
   - Restore vector stores if required by incident scope.
   - Confirm restored timestamp and RPO.

4. Verify integrity.
   - Run audit hash-chain verification.
   - Run service readiness probes.
   - Run Sprint 7 compliance smoke validation.

5. Rehydrate runtime state.
   - Recreate Redis Streams only from persisted task state.
   - Do not replay unsourced messages.
   - Escalate missing task state to human.

6. Resume service.
   - Re-enable internal-only capabilities first.
   - Validate Orchestrator to specialist-agent task flow.
   - Human compliance lead approves external-send unfreeze.

7. Close incident.
   - Record measured RTO and RPO.
   - Attach logs, restore evidence, and audit-chain verification.
   - Document unresolved risks and human overrides.

## Failure Conditions

- Audit chain does not verify
- Restored data exceeds RPO
- Compliance Service unavailable
- Network policies are missing or bypassed
- Any critical or high security finding lacks human approval
