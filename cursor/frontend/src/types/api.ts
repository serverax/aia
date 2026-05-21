export type WorkflowState = 'idle' | 'running' | 'paused' | 'completed' | 'error'

export type TaskStatus = 'pending' | 'in_progress' | 'approved' | 'rejected' | 'completed'

export interface OrchestratorTask {
  id: string
  type: string
  status: TaskStatus
  created_at: string
  created_by: string
  approvals_pending: string[]
  approval_reason: string
  progress?: number
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

