import { orchestratorClient } from '../orchestrator'
import type {
  ApprovalAuditEvent,
  ApprovalEscalationInput,
  ApprovalDecisionInput,
  ApprovalWorkflowRequest,
  ApprovalWorkflowDecisionInput,
  CreateApprovalWorkflowInput,
} from '../orchestrator'

export interface BulkActionResult {
  updatedCount: number
  failedCount: number
  failedIds: string[]
}

function withTimeout<T>(promise: Promise<T>, timeoutMs = 8000): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(`Request timed out after ${timeoutMs}ms`)), timeoutMs),
    ),
  ])
}

export const approvalService = {
  submitDecision(input: ApprovalDecisionInput) {
    return orchestratorClient.submitApprovalDecision(input)
  },
  listRequests() {
    return withTimeout(orchestratorClient.getApprovalWorkflows())
  },
  listAuditTrail(query?: { startDate?: string; endDate?: string }) {
    return withTimeout<ApprovalAuditEvent[]>(orchestratorClient.getApprovalAuditTrail(query))
  },
  createRequest(input: CreateApprovalWorkflowInput, requestor: string) {
    return withTimeout(orchestratorClient.createApprovalWorkflow(input, requestor))
  },
  submitWorkflowDecision(input: ApprovalWorkflowDecisionInput) {
    return withTimeout(orchestratorClient.submitApprovalWorkflowDecision(input))
  },
  escalateWorkflow(input: ApprovalEscalationInput) {
    return withTimeout(orchestratorClient.escalateApprovalWorkflow(input))
  },
  async submitBulkWorkflowDecision(input: {
    requestIds: string[]
    reviewerId: string
    decision: 'approve' | 'reject' | 'request_changes'
    feedback: string
  }): Promise<BulkActionResult> {
    return withTimeout(orchestratorClient.submitBulkApprovalWorkflowDecision(input))
  },
  async escalateBulkWorkflow(input: {
    requestIds: string[]
    reviewerId: string
    reason: string
  }): Promise<BulkActionResult> {
    return withTimeout(orchestratorClient.escalateBulkApprovalWorkflow(input))
  },
  restoreBulkWorkflowState(input: Array<{
    id: string
    status: ApprovalWorkflowRequest['status']
    reviewers: ApprovalWorkflowRequest['reviewers']
    feedback_thread: ApprovalWorkflowRequest['feedback_thread']
  }>) {
    return withTimeout(orchestratorClient.restoreBulkWorkflowState(input))
  },
}

