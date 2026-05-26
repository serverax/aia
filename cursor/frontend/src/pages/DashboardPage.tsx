import { useMemo, useState } from 'react'
import { ApprovalHistory, ApprovalModal } from '../components/ApprovalGate'
import { DashboardLayout, RealtimeMetrics, TaskQueue } from '../components/Dashboard'
import { useApprovalFlow } from '../hooks/useApprovalFlow'
import { useOrchestratorAPI } from '../hooks/useOrchestratorAPI'
import type { ApprovalRequest } from '../types/api'

export function DashboardPage() {
  const {
    snapshot,
    events,
    isConnected,
    connectionLabel,
    errorMessage,
    reconnectAttempt,
    retryConnection,
    pendingApprovals,
    approvalHistory,
    debugSimulateDisconnect,
  } = useOrchestratorAPI()
  const { submitDecision, isSubmitting, error } = useApprovalFlow()
  const [activeRequest, setActiveRequest] = useState<ApprovalRequest | null>(null)

  const onSubmit = async (decision: 'approve' | 'reject', reason: string) => {
    if (!activeRequest) return
    await submitDecision(activeRequest.id, decision, reason, 'human_reviewer')
    setActiveRequest(null)
  }

  const trendData = useMemo(() => {
    if (!snapshot) {
      return {
        completed: [0],
        pending: [0],
        approvals: [0],
        avgApprovalMs: [0],
      }
    }

    const recent = events.slice(0, 16).reverse()
    const completed = recent.map((event, index) => {
      if (event.type === 'task_updated' && (event.data as { status: string }).status === 'completed') {
        return index + 1
      }
      return index
    })
    const pending = recent.map((event, index) => {
      if (event.type === 'task_updated' && (event.data as { status: string }).status === 'pending') {
        return index + 1
      }
      return Math.max(0, index - 1)
    })
    const approvals = recent.map((_, index) => {
      const windowed = recent.slice(0, index + 1)
      const requested = windowed.filter((event) => event.type === 'approval_requested').length
      const decided = windowed.filter((event) => event.type === 'approval_decided').length
      return Math.max(0, requested - decided)
    })

    const baseAvg = snapshot.metrics.avg_approval_time_ms
    const avgApprovalMs = recent.map((_, index) => Math.max(0, baseAvg - (recent.length - index) * 120))

    return {
      completed: completed.length > 1 ? completed : [snapshot.metrics.tasks_completed, snapshot.metrics.tasks_completed],
      pending: pending.length > 1 ? pending : [snapshot.metrics.tasks_pending, snapshot.metrics.tasks_pending],
      approvals:
        approvals.length > 1 ? approvals : [pendingApprovals.length, pendingApprovals.length],
      avgApprovalMs: avgApprovalMs.length > 1 ? avgApprovalMs : [baseAvg, baseAvg],
    }
  }, [events, pendingApprovals.length, snapshot])

  const overview = useMemo(() => {
    if (!snapshot) {
      return {
        activeTasks: 0,
        stalledTasks: 0,
        urgentApprovals: 0,
        workflowState: 'idle',
      }
    }
    const activeTasks = snapshot.tasks.filter((task) => task.status === 'in_progress').length
    const stalledTasks = snapshot.tasks.filter((task) => (task.progress ?? 0) < 0.2 && task.status === 'pending').length
    const urgentApprovals = snapshot.tasks.filter((task) => task.approvals_pending.length > 0).length
    return {
      activeTasks,
      stalledTasks,
      urgentApprovals,
      workflowState: snapshot.state,
    }
  }, [snapshot])

  const workflowPillClass = useMemo(() => {
    if (overview.workflowState === 'running') return 'approved'
    if (overview.workflowState === 'error') return 'rejected'
    if (overview.workflowState === 'paused') return 'pending'
    return 'in_progress'
  }, [overview.workflowState])

  const recentActivity = useMemo(() => {
    return events.slice(0, 8).map((event) => {
      if (event.type === 'approval_requested') {
        const data = event.data as { task_id: string; reason: string }
        return {
          id: `${event.timestamp}-${event.type}`,
          label: 'Approval requested',
          detail: `Task ${data.task_id}: ${data.reason}`,
          timestamp: event.timestamp,
        }
      }
      if (event.type === 'approval_decided') {
        const data = event.data as { task_id: string; decision: string; decided_by: string }
        return {
          id: `${event.timestamp}-${event.type}`,
          label: 'Approval decided',
          detail: `Task ${data.task_id}: ${data.decision} by ${data.decided_by}`,
          timestamp: event.timestamp,
        }
      }
      if (event.type === 'task_updated') {
        const data = event.data as { task_id: string; status: string; progress?: number }
        return {
          id: `${event.timestamp}-${event.type}`,
          label: 'Task updated',
          detail: `Task ${data.task_id}: ${data.status} (${Math.round((data.progress ?? 0) * 100)}%)`,
          timestamp: event.timestamp,
        }
      }
      if (event.type === 'workflow_completed') {
        return {
          id: `${event.timestamp}-${event.type}`,
          label: 'Workflow completed',
          detail: 'Current workflow reached completed state.',
          timestamp: event.timestamp,
        }
      }
      if (event.type === 'error') {
        const data = event.data as { code: string; message: string }
        return {
          id: `${event.timestamp}-${event.type}`,
          label: 'Error',
          detail: `${data.code}: ${data.message}`,
          timestamp: event.timestamp,
        }
      }
      return {
        id: `${event.timestamp}-${event.type}`,
        label: event.type.replace('_', ' '),
        detail: 'Event received from orchestrator.',
        timestamp: event.timestamp,
      }
    })
  }, [events])

  const highlightedTaskIds = useMemo(() => {
    return Array.from(
      new Set(
        events
      .filter((event) => event.type === 'task_updated')
      .slice(0, 4)
      .map((event) => (event.data as { task_id: string }).task_id)
      ),
    )
  }, [events])

  return (
    <DashboardLayout
      connected={isConnected}
      connectionLabel={connectionLabel}
      onReconnectTest={debugSimulateDisconnect}
    >
      {!snapshot ? <p className="loading">Loading orchestrator data...</p> : null}
      {!isConnected ? (
        <section className="card status-alert">
          <h3>Connection degraded</h3>
          <p>{errorMessage ?? `Disconnected from orchestrator. Reconnect attempt ${reconnectAttempt}.`}</p>
          <button type="button" onClick={retryConnection}>
            Retry now
          </button>
        </section>
      ) : null}

      {snapshot ? (
        <div className="dashboard-overview">
          <section className="card overview-card">
            <h2>Workflow Overview</h2>
            <div className="overview-grid">
              <article>
                <span>Workflow State</span>
                <strong className={`pill ${workflowPillClass}`}>{overview.workflowState}</strong>
              </article>
              <article>
                <span>Active Tasks</span>
                <strong>{overview.activeTasks}</strong>
              </article>
              <article>
                <span>Stalled Tasks</span>
                <strong>{overview.stalledTasks}</strong>
              </article>
              <article>
                <span>Urgent Approvals</span>
                <strong>{overview.urgentApprovals}</strong>
              </article>
            </div>
            <small>Last orchestrator update: {new Date(snapshot.last_update).toLocaleString()}</small>
          </section>
          <section className="card overview-card">
            <h2>Recent Activity</h2>
            <ul className="activity-list">
              {recentActivity.length === 0 ? <li>No events yet.</li> : null}
              {recentActivity.map((item) => (
                <li key={item.id}>
                  <p>
                    <strong>{item.label}</strong>
                  </p>
                  <p>{item.detail}</p>
                  <small>{new Date(item.timestamp).toLocaleString()}</small>
                </li>
              ))}
            </ul>
          </section>
        </div>
      ) : null}

      {snapshot ? (
        <div className="dashboard-grid dashboard-grid-main">
          <RealtimeMetrics
            metrics={snapshot.metrics}
            pendingApprovals={pendingApprovals.length}
            trends={trendData}
          />
          <TaskQueue tasks={snapshot.tasks} highlightedTaskIds={highlightedTaskIds} />
          <ApprovalHistory
            pending={pendingApprovals}
            history={approvalHistory}
            onOpenRequest={setActiveRequest}
          />
        </div>
      ) : null}

      {error ? <p className="error">{error}</p> : null}

      <ApprovalModal
        request={activeRequest}
        isSubmitting={isSubmitting}
        onClose={() => setActiveRequest(null)}
        onSubmit={onSubmit}
      />
    </DashboardLayout>
  )
}

