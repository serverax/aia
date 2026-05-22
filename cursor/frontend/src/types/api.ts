export type WorkflowState = 'idle' | 'running' | 'paused' | 'completed' | 'error'

export type TaskStatus = 'pending' | 'in_progress' | 'approved' | 'rejected' | 'completed'

export type PolicyOutcome = 'matched' | 'rejected'

export interface PolicyEvaluation {
  policy_id: string
  title: string
  source: string
  outcome: PolicyOutcome
  rationale: string
  evaluated_by: string
  url?: string
}

export interface OrchestratorTask {
  id: string
  type: string
  status: TaskStatus
  created_at: string
  created_by: string
  approvals_pending: string[]
  approval_reason: string
  progress?: number
  policy_evaluations?: PolicyEvaluation[]
}

export interface OrchestratorMetrics {
  tasks_completed: number
  tasks_pending: number
  avg_approval_time_ms: number
}

export interface OrchestratorSnapshot {
  id: string
  state: WorkflowState
  tasks: OrchestratorTask[]
  metrics: OrchestratorMetrics
  last_update: string
}

export interface ApprovalRequest {
  id: string
  taskId: string
  title: string
  summary: string
  requestedBy: string
  createdAt: string
  status: 'pending' | 'approve' | 'reject'
}

export interface ApprovalDecisionInput {
  approvalId: string
  decision: 'approve' | 'reject'
  reason: string
  decided_by: string
}

export interface ApprovalDecisionResult {
  id: string
  decision: 'approve' | 'reject'
  timestamp: string
  next_state: string
}

export type ApprovalRequestType = 'policy_change' | 'document_release' | 'exception'
export type ApprovalWorkflowStatus = 'pending' | 'in_progress' | 'approved' | 'rejected'
export type ReviewerStatus = 'pending' | 'approved' | 'rejected' | 'request_changes'
export type ApprovalStrategy = 'all_must_approve' | 'any_can_approve' | 'weighted_voting'

export interface ApprovalReviewer {
  user_id: string
  status: ReviewerStatus
  feedback?: string
  signed_at?: string
}

export interface ApprovalFeedbackItem {
  id: string
  author: string
  comment: string
  created_at: string
}

export type ConfidenceBand = 'low' | 'medium' | 'high'

export interface ConfidenceFactor {
  label: string
  impact: 'positive' | 'negative' | 'neutral'
  detail: string
}

export interface RecommendationConfidence {
  score: number
  band: ConfidenceBand
  factors: ConfidenceFactor[]
  requires_acknowledgement: boolean
}

export interface ExplanationClause {
  clause_id: string
  title: string
  outcome: PolicyOutcome
  rationale: string
  evidence: string
}

export interface DecisionPathStep {
  actor: string
  action: string
  rationale: string
  timestamp: string
}

export interface DecisionExplanation {
  summary: string
  clauses: ExplanationClause[]
  decision_path: DecisionPathStep[]
}

export interface ApprovalWorkflowRequest {
  id: string
  request_type: ApprovalRequestType
  title: string
  description: string
  requestor: string
  requested_at: string
  deadline: string
  reviewers: ApprovalReviewer[]
  status: ApprovalWorkflowStatus
  approval_strategy: ApprovalStrategy
  metadata: {
    related_document_id?: string
    risk_score?: number
    template_id?: string
  }
  feedback_thread: ApprovalFeedbackItem[]
  decision_explanation: DecisionExplanation
  recommendation_confidence: RecommendationConfidence
}

export interface CreateApprovalWorkflowInput {
  request_type: ApprovalRequestType
  title: string
  description: string
  deadline: string
  reviewers: string[]
  approval_strategy: ApprovalStrategy
  metadata: {
    related_document_id?: string
    risk_score?: number
    template_id?: string
  }
}

export interface ApprovalWorkflowDecisionInput {
  requestId: string
  reviewerId: string
  decision: 'approve' | 'reject'
  feedback: string
}

export interface ApprovalEscalationInput {
  requestId: string
  reviewerId: string
  reason: string
}

export type ApprovalAuditOutcome = 'approved' | 'rejected' | 'overrode' | 'request_changes'

export interface ApprovalAuditEvent {
  id: string
  request_id: string
  request_title: string
  actor: string
  outcome: ApprovalAuditOutcome
  policy: string
  reason: string
  timestamp: string
  explanation: DecisionExplanation
  confidence: RecommendationConfidence
  event_type?: 'decision' | 'bulk_action' | 'template' | 'undo'
  metadata?: Record<string, string | number | boolean | string[]>
}

export type OrchestratorEventType =
  | 'task_created'
  | 'task_updated'
  | 'approval_requested'
  | 'approval_decided'
  | 'workflow_completed'
  | 'error'

export interface TaskUpdatedEventData {
  task_id: string
  status: TaskStatus
  progress?: number
}

export interface ApprovalRequestedEventData {
  task_id: string
  approvers: string[]
  reason: string
}

export interface ApprovalDecidedEventData {
  approval_id: string
  task_id: string
  decision: 'approve' | 'reject'
  decided_by: string
  reason: string
}

export interface WorkflowCompletedEventData {
  workflow_id: string
  state: Extract<WorkflowState, 'completed'>
}

export interface ErrorEventData {
  code: string
  message: string
}

export type OrchestratorEventData =
  | OrchestratorTask
  | TaskUpdatedEventData
  | ApprovalRequestedEventData
  | ApprovalDecidedEventData
  | WorkflowCompletedEventData
  | ErrorEventData

export interface OrchestratorEventEnvelope {
  type: OrchestratorEventType
  timestamp: string
  data: OrchestratorEventData
}

