# Approval UI Integration (Sprint 5.2)

## Frontend integration points

Approval UI currently uses `orchestratorClient` mock methods for local workflows:

- `getApprovalWorkflows()`
- `createApprovalWorkflow(input, requestor)`
- `submitApprovalWorkflowDecision(input)`
- `escalateApprovalWorkflow(input)`

These methods are wrapped in `approvalService` with an 8s timeout for loading-state safety.

Audit Trail endpoint contract (5.4):

- `getApprovalAuditTrail({ startDate?, endDate? })`
- query params mapped as `start_date` and `end_date`
- timeline exports (`CSV`/`JSON`) are generated from currently filtered rows

## Analyst service integration contract

The Approval Request Form can call Analyst service endpoint:

- `POST /analyst/approval/evaluate`

File: `services/analyst_agent/analyst_service.py`

### Request schema

```json
{
  "request_type": "policy_change|document_release|exception",
  "title": "string",
  "description": "string",
  "requestor": "string",
  "deadline": "ISO8601",
  "approval_strategy": "all_must_approve|any_can_approve|weighted_voting",
  "metadata": {
    "risk_score": 7.5
  }
}
```

### Response schema

```json
{
  "request_id": "APR-EVAL-...",
  "risk_score": 8.4,
  "sla_hours_recommended": 24,
  "recommended_reviewers": [
    "you@synthetic.io",
    "compliance_officer@synthetic.io",
    "security_lead@synthetic.io"
  ],
  "analyst_summary": "string"
}
```

## Error handling

- `400`: unsupported request type or approval strategy
- `422`: schema/validation failure (missing fields, bad types)
- `500`: runtime/internal failure

Frontend behavior:

- request-level loading indicator (`isSubmitting`, `isLoading`)
- timeout-based fail-safe (`Request timed out after 8000ms`)
- user-facing error message on create/decision/escalation failures

## Mapping into Approval UI

- `recommended_reviewers` can prefill `ReviewerSelector`
- `sla_hours_recommended` can inform deadline defaults
- `risk_score` and summary map into `metadata.risk_score` and request description

