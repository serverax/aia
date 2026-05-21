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
        <div className="dashboard-grid">
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

