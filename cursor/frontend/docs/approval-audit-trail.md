# Sprint 5.3 Audit Trail Display

## Scope delivered

- Timeline displays compliance decisions in chronological order.
- Each event includes actor, outcome, timestamp, policy identifier, and reason.
- Filters available for:
  - agent (`actor`)
  - policy (`related_document_id` or `request_type`)
  - outcome (`approved|rejected|overrode`)
- Timeline refreshes after approval actions (`approve`, `reject`, `request changes`, `escalate`).

## Data contract

`ApprovalAuditEvent`:

```json
{
  "id": "AUD-...",
  "request_id": "APR-001",
  "request_title": "Q2 Compliance Review Sign-off",
  "actor": "you@synthetic.io",
  "outcome": "approved",
  "policy": "DOC_123",
  "reason": "Approved after reviewing exceptions.",
  "timestamp": "2026-05-21T09:00:00Z"
}
```

## Integration flow

1. `ApprovalRequestPage` calls `approvalService.listAuditTrail()`.
2. Service calls `orchestratorClient.getApprovalAuditTrail()` with timeout protection.
3. Mock orchestrator appends audit events for create, decision, and escalation actions.
4. UI refreshes queue + timeline together after each action.
