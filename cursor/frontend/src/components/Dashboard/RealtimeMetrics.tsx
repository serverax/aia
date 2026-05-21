import type { OrchestratorMetrics } from '../../types/api'

interface RealtimeMetricsProps {
  metrics: OrchestratorMetrics
  pendingApprovals: number
  trends: {
    completed: number[]
    pending: number[]
    approvals: number[]
    avgApprovalMs: number[]
  }
}

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return <div className="sparkline-empty" />

  const width = 120
  const height = 34
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width
      const y = height - ((value - min) / range) * height
      return `${x},${y}`
    })
    .join(' ')

  return (
    <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <polyline points={points} />
    </svg>
  )
}

export function RealtimeMetrics({ metrics, pendingApprovals, trends }: RealtimeMetricsProps) {
  const metricKey = `${metrics.tasks_completed}-${metrics.tasks_pending}-${pendingApprovals}-${Math.round(metrics.avg_approval_time_ms)}`

  return (
    <section className="card">
      <h2>Realtime Metrics</h2>
      <div key={metricKey} className="metrics-grid metrics-pulse">
        <article>
          <span>Tasks Completed</span>
          <strong>{metrics.tasks_completed}</strong>
          <Sparkline values={trends.completed} />
        </article>
        <article>
          <span>Tasks Pending</span>
          <strong>{metrics.tasks_pending}</strong>
          <Sparkline values={trends.pending} />
        </article>
        <article>
          <span>Pending Approvals</span>
          <strong>{pendingApprovals}</strong>
          <Sparkline values={trends.approvals} />
        </article>
        <article>
          <span>Avg Approval Time</span>
          <strong>{Math.round(metrics.avg_approval_time_ms)} ms</strong>
          <Sparkline values={trends.avgApprovalMs} />
        </article>
      </div>
    </section>
  )
}

