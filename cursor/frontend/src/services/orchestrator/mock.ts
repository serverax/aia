import type {
  ApprovalDecisionInput,
  ApprovalDecisionResult,
  ApprovalRequest,
  OrchestratorEventEnvelope,
  OrchestratorMetrics,
  OrchestratorSnapshot,
  OrchestratorTask,
} from './types'

type EventHandler = (event: OrchestratorEventEnvelope) => void

const nowIso = () => new Date().toISOString()

const initialTasks: OrchestratorTask[] = [
  {
    id: 'task_1',
    type: 'precedent_research',
    status: 'in_progress',
    created_at: nowIso(),
    created_by: 'analyst',
    approvals_pending: ['human_reviewer'],
    approval_reason: 'Approve precedent shortlist before compliance screening',
    progress: 0.4,
  },
  {
    id: 'task_2',
    type: 'compliance_review',
    status: 'pending',
    created_at: nowIso(),
    created_by: 'compliance_officer',
    approvals_pending: [],
    approval_reason: '',
    progress: 0,
  },
]

const initialApprovals: ApprovalRequest[] = [
  {
    id: 'approval_1',
    taskId: 'task_1',
    title: 'Approve precedent shortlist',
    summary: 'Analyst prepared top 5 precedents; approve before compliance review.',
    requestedBy: 'analyst',
    createdAt: nowIso(),
    status: 'pending',
  },
]

export class MockOrchestratorClient {
  private handlers: Set<EventHandler> = new Set()
  private connectionHandlers: Set<(connected: boolean) => void> = new Set()
  private intervalId?: number
  private tasks: OrchestratorTask[] = structuredClone(initialTasks)
  private approvals: ApprovalRequest[] = structuredClone(initialApprovals)
  private connected = false
  private workflowId = 'wf-001'

  connect() {
    if (this.connected) return
    this.connected = true
    this.emitConnection(true)

    this.intervalId = window.setInterval(() => {
      this.simulateTaskMotion()
    }, 4000)
  }

  disconnect() {
    if (this.intervalId) window.clearInterval(this.intervalId)
    this.intervalId = undefined
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
    return this.snapshot()
  }

  async submitApprovalDecision(
    input: ApprovalDecisionInput,
  ): Promise<ApprovalDecisionResult> {
    this.approvals = this.approvals.map((approval) =>
      approval.id === input.approvalId
        ? {
            ...approval,
            status: input.decision,
          }
        : approval,
    )

    const updated = this.approvals.find((a) => a.id === input.approvalId)
    const targetTask = updated ? this.tasks.find((task) => task.id === updated.taskId) : undefined

    if (targetTask) {
      targetTask.status = input.decision === 'approve' ? 'approved' : 'rejected'
      targetTask.approvals_pending = []
      targetTask.progress = input.decision === 'approve' ? 0.8 : targetTask.progress

      this.publish({
        type: 'task_updated',
        timestamp: nowIso(),
        data: {
          task_id: targetTask.id,
          status: targetTask.status,
          progress: targetTask.progress,
        },
      })
    }

    if (updated) {
      this.publish({
        type: 'approval_decided',
        timestamp: nowIso(),
        data: {
          approval_id: updated.id,
          task_id: updated.taskId,
          decision: input.decision,
          decided_by: input.decided_by,
          reason: input.reason,
        },
      })
    }

    const nextPending = this.tasks.find((task) => task.status === 'pending')
    if (nextPending && input.decision === 'approve') {
      nextPending.status = 'in_progress'
      nextPending.progress = 0.2
      this.publish({
        type: 'task_updated',
        timestamp: nowIso(),
        data: {
          task_id: nextPending.id,
          status: nextPending.status,
          progress: nextPending.progress,
        },
      })
    }

    return {
      id: input.approvalId,
      decision: input.decision,
      timestamp: nowIso(),
      next_state: input.decision === 'approve' ? 'resume_workflow' : 'halt_workflow',
    }
  }

  private publish(event: OrchestratorEventEnvelope) {
    this.handlers.forEach((handler) => handler(event))
  }

  private emitConnection(connected: boolean) {
    this.connectionHandlers.forEach((handler) => handler(connected))
  }

  private snapshot(): OrchestratorSnapshot {
    return {
      id: this.workflowId,
      state: this.workflowState(),
      metrics: this.metrics(),
      tasks: this.tasks,
      last_update: nowIso(),
    }
  }

  getApprovals() {
    return this.approvals
  }

  private metrics(): OrchestratorMetrics {
    return {
      tasks_completed: this.tasks.filter((task) => task.status === 'completed').length,
      tasks_pending: this.tasks.filter((task) => task.status === 'pending').length,
      avg_approval_time_ms: 4200,
    }
  }

  private workflowState(): OrchestratorSnapshot['state'] {
    if (this.tasks.every((task) => task.status === 'completed')) return 'completed'
    if (this.tasks.some((task) => task.status === 'rejected')) return 'paused'
    if (this.connected) return 'running'
    return 'idle'
  }

  private simulateTaskMotion() {
    if (!this.connected) return

    const target = this.tasks.find((task) => task.status === 'in_progress')
    if (!target) {
      const pending = this.tasks.find((task) => task.status === 'pending')
      if (pending) {
        pending.status = 'in_progress'
        pending.progress = 0.15
        this.publish({
          type: 'task_updated',
          timestamp: nowIso(),
          data: {
            task_id: pending.id,
            status: pending.status,
            progress: pending.progress,
          },
        })
      }
      return
    }

    if ((target.progress ?? 0) >= 0.85) {
      target.status = 'completed'
      target.progress = 1
      this.publish({
        type: 'task_updated',
        timestamp: nowIso(),
        data: {
          task_id: target.id,
          status: target.status,
          progress: target.progress,
        },
      })
      return
    }

    target.progress = Math.min((target.progress ?? 0) + 0.2, 0.9)
    this.publish({
      type: 'task_updated',
      timestamp: nowIso(),
      data: {
        task_id: target.id,
        status: target.status,
        progress: target.progress,
      },
    })

    if (Math.random() > 0.55) {
      const existingPending = this.approvals.some(
        (approval) => approval.taskId === target.id && approval.status === 'pending',
      )
      if (!existingPending) {
        const approval: ApprovalRequest = {
          id: `approval_${Date.now()}`,
          taskId: target.id,
          title: `Approval required: ${target.type}`,
          summary: `${target.created_by} requests a human decision to continue.`,
          requestedBy: target.created_by,
          createdAt: nowIso(),
          status: 'pending',
        }
        this.approvals = [approval, ...this.approvals]
        target.approvals_pending = ['human_reviewer']
        target.approval_reason = approval.summary
        this.publish({
          type: 'approval_requested',
          timestamp: nowIso(),
          data: {
            task_id: target.id,
            approvers: ['human_reviewer'],
            reason: approval.summary,
          },
        })
      }
    }
  }
}

