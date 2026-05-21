# Sprint 6 Checkpoint A Contract Updates

## Updated approval response model

`ApprovalWorkflowRequest` now includes:

- `decision_explanation`
  - `summary`
  - `clauses[]` with `clause_id`, `title`, `outcome`, `rationale`, `evidence`
  - `decision_path[]` with `actor`, `action`, `rationale`, `timestamp`
- `recommendation_confidence`
  - `score` (`0.0-1.0`)
  - `band` (`low|medium|high`)
  - `factors[]` (`label`, `impact`, `detail`)
  - `requires_acknowledgement` (boolean)

## Updated audit response model

`ApprovalAuditEvent` now includes:

- `explanation` (`DecisionExplanation`)
- `confidence` (`RecommendationConfidence`)

This enables audit consumers to reconstruct the "why" and confidence state at the moment each event is recorded.

## Guardrail behavior

If `recommendation_confidence.requires_acknowledgement` is `true`, decision actions are blocked until reviewer checks the explicit acknowledgement control in `ApprovalDetail`.
