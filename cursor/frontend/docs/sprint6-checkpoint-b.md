# Sprint 6 Checkpoint B: Bulk Workflows and Templates

## 6.3 Bulk approval workflows

Implemented queue-level batch actions:

- `Bulk Approve`
- `Bulk Reject`
- `Bulk Escalate`

Behavior:

- User can select individual requests or use **Select all visible**.
- Batch actions execute against selected request IDs.
- Queue + audit timeline refresh after each batch action.
- Status message shows count of affected requests.

Service/methods:

- `approvalService.submitBulkWorkflowDecision(...)`
- `approvalService.escalateBulkWorkflow(...)`
- `orchestratorClient.submitBulkApprovalWorkflowDecision(...)`
- `orchestratorClient.escalateBulkApprovalWorkflow(...)`

## 6.4 Custom approval templates

Added request template presets in Approval Request form:

- `Policy Change Standard Review`
- `Exception Fastlane`
- `Document Release`

Each preset applies defaults for:

- request type
- approval strategy
- default reviewers
- risk score
- title + description seed text
- deadline offset

Templates are frontend presets and can be converted to backend-driven templates in Sprint 7+ without UI changes.
