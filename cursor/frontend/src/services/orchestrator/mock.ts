import type {
  ApprovalAuditEvent,
  ApprovalAuditOutcome,
  ApprovalDecisionInput,
  ApprovalDecisionResult,
  ApprovalEscalationInput,
  ApprovalRequest,
  ApprovalReviewer,
  ApprovalWorkflowDecisionInput,
  ApprovalWorkflowRequest,
  CreateApprovalWorkflowInput,
  DecisionExplanation,
  OrchestratorEventEnvelope,
  OrchestratorMetrics,
  OrchestratorSnapshot,
  OrchestratorTask,
  RecommendationConfidence,
} from './types'

type EventHandler = (event: OrchestratorEventEnvelope) => void

const nowIso = () => new Date().toISOString()

function buildConfidence(score: number): RecommendationConfidence {
  const safe = Math.max(0, Math.min(1, score))
  const band = safe < 0.6 ? 'low' : safe < 0.8 ? 'medium' : 'high'
  return {
    score: safe,
    band,
    factors: [
      {
        label: 'Policy evidence',
        impact: band === 'low' ? 'negative' : 'positive',
        detail: band === 'low' ? 'Evidence incomplete.' : 'Evidence complete.',
      },
    ],
    requires_acknowledgement: band === 'low',
  }
}

function buildExplanation(requestId: string): DecisionExplanation {
  return {
    summary: `Automated recommendation prepared for ${requestId}.`,
    clauses: [
      {
        clause_id: 'C-1',
        title: 'Policy mapping',
        outcome: 'matched',
        rationale: 'Mapped against required controls.',
        evidence: 'Policy matrix v2.',
      },
    ],
    decision_path: [
      {
        actor: 'analyst@synthetic.io',
        action: 'generated recommendation',
        rationale: 'Baseline control checks complete.',
        timestamp: nowIso(),
      },
    ],
  }
}

function buildInitialWorkflows(): ApprovalWorkflowRequest[] {
  return Array.from({ length: 60 }, (_, idx) => {
    const i = idx + 1
    const isLowConfidence = i % 8 === 0
    return {
      id: `APR-${String(i).padStart(3, '0')}`,
      request_type: i % 3 === 0 ? 'exception' : i % 2 === 0 ? 'document_release' : 'policy_change',
      title: `Approval Request ${i}`,
      description: `Review and approve request ${i}.`,
      requestor: i % 4 === 0 ? 'editor@synthetic.io' : 'compliance_officer@synthetic.io',
      requested_at: new Date(Date.now() - i * 60 * 60 * 1000).toISOString(),
      deadline: new Date(Date.now() + (24 - (i % 10)) * 60 * 60 * 1000).toISOString(),
      reviewers: [
        { user_id: 'you@synthetic.io', status: 'pending' },
        { user_id: 'compliance_officer@synthetic.io', status: 'pending' },
      ],
      status: i % 6 === 0 ? 'in_progress' : 'pending',
      approval_strategy: i % 2 === 0 ? 'all_must_approve' : 'any_can_approve',
      metadata: {
        related_document_id: `DOC-${100 + i}`,
        risk_score: (i % 9) + 1,
      },
      feedback_thread: isLowConfidence
        ? [
            {
              id: `FDBK-${i}`,
              author: 'reviewer@synthetic.io',
              comment: 'Escalated for manual override.',
              created_at: new Date(Date.now() - i * 30 * 60 * 1000).toISOString(),
            },
          ]
        : [],
      decision_explanation: buildExplanation(`APR-${String(i).padStart(3, '0')}`),
      recommendation_confidence: buildConfidence(isLowConfidence ? 0.52 : 0.86),
    }
  })
}

const initialTasks: OrchestratorTask[] = [
  {
    id: 'task_1',
    type: 'approval_pipeline',
    status: 'in_progress',
    created_at: nowIso(),
    created_by: 'orchestrator',
    approvals_pending: ['you@synthetic.io'],
    approval_reason: 'Batch requires reviewer sign-off.',
    progress: 0.5,
  },
]

const initialApprovals: ApprovalRequest[] = [
  {
    id: 'approval_1',
    taskId: 'task_1',
    title: 'Approve workflow batch',
    summary: 'Batch ready for decision.',
    requestedBy: 'orchestrator',
    createdAt: nowIso(),
    status: 'pending',
  },
]

export class MockOrchestratorClient {
  private handlers: Set<EventHandler> = new Set()
  private connectionHandlers: Set<(connected: boolean) => void> = new Set()
  private tasks: OrchestratorTask[] = structuredClone(initialTasks)
  private approvals: ApprovalRequest[] = structuredClone(initialApprovals)
  private approvalWorkflows: ApprovalWorkflowRequest[] = buildInitialWorkflows()
  private auditTrail: ApprovalAuditEvent[] = []
  private connected = false
  private workflowId = 'wf-001'

  connect() {
    this.connected = true
    this.emitConnection(true)
  }

  disconnect() {
    this.connected = false
    this.emitConnection(false)
  }

  debugSimulateDisconnect() {
    this.disconnect()
  }

  subscribe(handler: EventHandler) {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  subscribeConnection(handler: (connected: boolean) => void) {
    this.connectionHandlers.add(handler)
    return () => this.connectionHandlers.delete(handler)
  }

  async getSnapshot(): Promise<OrchestratorSnapshot> {
    return {
      id: this.workflowId,
      state: this.connected ? 'running' : 'idle',
      metrics: this.metrics(),
      tasks: this.tasks,
      last_update: nowIso(),
    }
  }

  getApprovals() {
    return this.approvals
  }

  getApprovalWorkflows() {
    return this.approvalWorkflows
  }

  getApprovalAuditTrail(query?: { startDate?: string; endDate?: string }) {
    const start = query?.startDate ? new Date(query.startDate).getTime() : Number.MIN_SAFE_INTEGER
    const end = query?.endDate ? new Date(query.endDate).getTime() : Number.MAX_SAFE_INTEGER
    return this.auditTrail.filter((event) => {
      const ts = new Date(event.timestamp).getTime()
      return ts >= start && ts <= end
    })
  }

  async createApprovalWorkflow(input: CreateApprovalWorkflowInput, requestor: string) {
    const created: ApprovalWorkflowRequest = {
      id: `APR-${String(this.approvalWorkflows.length + 1).padStart(3, '0')}`,
      request_type: input.request_type,
      title: input.title,
      description: input.description,
      requestor,
      requested_at: nowIso(),
      deadline: input.deadline,
      reviewers: input.reviewers.map((reviewer): ApprovalReviewer => ({ user_id: reviewer, status: 'pending' })),
      status: 'pending',
      approval_strategy: input.approval_strategy,
      metadata: input.metadata,
      feedback_thread: [],
      decision_explanation: buildExplanation(input.title),
      recommendation_confidence: buildConfidence(0.82),
    }
    this.approvalWorkflows = [created, ...this.approvalWorkflows]
    if (input.metadata.template_id) {
      this.auditTrail = [
        {
          ...this.makeAudit(created, requestor, 'approved', `Template applied: ${input.metadata.template_id}`),
          event_type: 'template',
          metadata: {
            template_id: input.metadata.template_id,
            preview_seen: true,
          },
        },
        ...this.auditTrail,
      ]
    }
    return created
  }

  submitApprovalWorkflowDecision(input: ApprovalWorkflowDecisionInput) {
    let updated: ApprovalWorkflowRequest | undefined
    this.approvalWorkflows = this.approvalWorkflows.map((request) => {
      if (request.id !== input.requestId) return request
      const nextReviewers: ApprovalReviewer[] = request.reviewers.map((reviewer) => {
        if (reviewer.user_id !== input.reviewerId) return reviewer
        return {
          ...reviewer,
          status: (input.decision === 'approve' ? 'approved' : 'rejected') as 'approved' | 'rejected',
          feedback: input.feedback,
          signed_at: nowIso(),
        }
      })
      const hasRejection = nextReviewers.some((reviewer) => reviewer.status === 'rejected')
      const allApproved = nextReviewers.every((reviewer) => reviewer.status === 'approved')
      const nextStatus = hasRejection ? 'rejected' : allApproved ? 'approved' : 'in_progress'
      const nextRequest: ApprovalWorkflowRequest = {
        ...request,
        reviewers: nextReviewers,
        status: nextStatus,
        feedback_thread: [
          ...request.feedback_thread,
          { id: `FDBK-${Date.now()}`, author: input.reviewerId, comment: input.feedback, created_at: nowIso() },
        ],
      }
      updated = nextRequest
      return nextRequest
    })
    if (updated) {
      this.auditTrail = [
        this.makeAudit(updated, input.reviewerId, input.decision === 'approve' ? 'approved' : 'rejected', input.feedback),
        ...this.auditTrail,
      ]
    }
    return updated
  }

  submitBulkApprovalWorkflowDecision(input: {
    requestIds: string[]
    reviewerId: string
    decision: 'approve' | 'reject' | 'request_changes'
    feedback: string
  }) {
    const failedIds: string[] = []
    let updatedCount = 0
    input.requestIds.forEach((requestId) => {
      const target = this.approvalWorkflows.find((request) => request.id === requestId)
      if (!target || target.status === 'approved' || target.status === 'rejected') {
        failedIds.push(requestId)
        return
      }
      const mappedDecision = input.decision === 'request_changes' ? 'reject' : input.decision
      this.submitApprovalWorkflowDecision({
        requestId,
        reviewerId: input.reviewerId,
        decision: mappedDecision,
        feedback: input.feedback,
      })
      if (input.decision === 'request_changes') {
        const latest = this.approvalWorkflows.find((request) => request.id === requestId)
        if (latest) {
          latest.reviewers = latest.reviewers.map((reviewer) =>
            reviewer.user_id === input.reviewerId ? { ...reviewer, status: 'request_changes' } : reviewer,
          )
          this.auditTrail = [
            {
              ...this.makeAudit(latest, input.reviewerId, 'request_changes', input.feedback),
              event_type: 'bulk_action',
              metadata: {
                action: 'bulk_request_changes',
              },
            },
            ...this.auditTrail,
          ]
        }
      }
      updatedCount += 1
    })
    const latencyMs = 40 + Math.floor(Math.random() * 30)
    this.auditTrail = [
      {
        id: `AUD-BULK-${Date.now()}`,
        request_id: 'bulk',
        request_title: 'Bulk operation summary',
        actor: input.reviewerId,
        outcome: input.decision === 'approve' ? 'approved' : input.decision === 'reject' ? 'rejected' : 'request_changes',
        policy: 'bulk',
        reason: `Bulk ${input.decision} processed`,
        timestamp: nowIso(),
        explanation: buildExplanation('bulk'),
        confidence: buildConfidence(0.88),
        event_type: 'bulk_action',
        metadata: {
          updatedCount,
          failedCount: failedIds.length,
          failedIds,
          write_latency_ms: latencyMs,
        },
      },
      ...this.auditTrail,
    ]
    return { updatedCount, failedCount: failedIds.length, failedIds }
  }

  escalateApprovalWorkflow(input: ApprovalEscalationInput) {
    let updated: ApprovalWorkflowRequest | undefined
    this.approvalWorkflows = this.approvalWorkflows.map((request) => {
      if (request.id !== input.requestId) return request
      updated = {
        ...request,
        feedback_thread: [
          ...request.feedback_thread,
          { id: `FDBK-${Date.now()}`, author: input.reviewerId, comment: `Escalated: ${input.reason}`, created_at: nowIso() },
        ],
      }
      return updated
    })
    if (updated) {
      this.auditTrail = [this.makeAudit(updated, input.reviewerId, 'overrode', input.reason), ...this.auditTrail]
    }
    return updated
  }

  escalateBulkApprovalWorkflow(input: { requestIds: string[]; reviewerId: string; reason: string }) {
    const failedIds: string[] = []
    let updatedCount = 0
    input.requestIds.forEach((requestId) => {
      const target = this.approvalWorkflows.find((request) => request.id === requestId)
      if (!target) {
        failedIds.push(requestId)
        return
      }
      this.escalateApprovalWorkflow({ requestId, reviewerId: input.reviewerId, reason: input.reason })
      updatedCount += 1
    })
    return { updatedCount, failedCount: failedIds.length, failedIds }
  }

  restoreBulkWorkflowState(
    input: Array<{
      id: string
      status: ApprovalWorkflowRequest['status']
      reviewers: ApprovalWorkflowRequest['reviewers']
      feedback_thread: ApprovalWorkflowRequest['feedback_thread']
    }>,
  ) {
    const restoreById = new Map(input.map((item) => [item.id, item]))
    this.approvalWorkflows = this.approvalWorkflows.map((request) => {
      const restore = restoreById.get(request.id)
      if (!restore) return request
      return {
        ...request,
        status: restore.status,
        reviewers: restore.reviewers,
        feedback_thread: restore.feedback_thread,
      }
    })
    this.auditTrail = [
      {
        id: `AUD-UNDO-${Date.now()}`,
        request_id: 'bulk',
        request_title: 'Bulk action rollback',
        actor: 'you@synthetic.io',
        outcome: 'overrode',
        policy: 'undo-window',
        reason: 'Bulk action reverted in 30-second undo window.',
        timestamp: nowIso(),
        explanation: buildExplanation('undo'),
        confidence: buildConfidence(0.9),
        event_type: 'undo',
        metadata: {
          restored_ids: input.map((item) => item.id),
          restored_count: input.length,
          write_latency_ms: 35,
        },
      },
      ...this.auditTrail,
    ]
  }

  async submitApprovalDecision(input: ApprovalDecisionInput): Promise<ApprovalDecisionResult> {
    return {
      id: input.approvalId,
      decision: input.decision,
      timestamp: nowIso(),
      next_state: input.decision === 'approve' ? 'resume_workflow' : 'halt_workflow',
    }
  }

  private makeAudit(
    request: ApprovalWorkflowRequest,
    actor: string,
    outcome: ApprovalAuditOutcome,
    reason: string,
  ): ApprovalAuditEvent {
    return {
      id: `AUD-${Date.now()}-${request.id}`,
      request_id: request.id,
      request_title: request.title,
      actor,
      outcome,
      policy: request.metadata.related_document_id ?? request.request_type,
      reason,
      timestamp: nowIso(),
      explanation: request.decision_explanation,
      confidence: request.recommendation_confidence,
    }
  }

  private emitConnection(connected: boolean) {
    this.connectionHandlers.forEach((handler) => handler(connected))
  }

  private metrics(): OrchestratorMetrics {
    return {
      tasks_completed: this.tasks.filter((task) => task.status === 'completed').length,
      tasks_pending: this.tasks.filter((task) => task.status === 'pending').length,
      avg_approval_time_ms: 900,
    }
  }
}
