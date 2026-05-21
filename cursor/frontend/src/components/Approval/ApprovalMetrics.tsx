import type { ApprovalWorkflowRequest } from '../../types/api'

interface ApprovalMetricsProps {
  avgCycleHours: number
  slaComplianceRate: number
  reviewerRanking: Array<{ reviewer: string; avgHours: number }>
  bottlenecks: ApprovalWorkflowRequest[]
}

export function ApprovalMetrics({
  avgCycleHours,
  slaComplianceRate,
  reviewerRanking,
  bottlenecks,
}: ApprovalMetricsProps) {
  return (
    <section className="card approval-card">
      <h2>Approval Metrics</h2>
      <div className="metrics-grid">
        <article>
          <span>Average Cycle Time</span>
          <strong>{avgCycleHours} h</strong>
        </article>
        <article>
          <span>SLA Compliance</span>
          <strong>{slaComplianceRate}%</strong>
        </article>
      </div>

      <h3>Reviewer Speed Ranking</h3>
      <ul className="approval-list">
        {reviewerRanking.map((item) => (
          <li key={item.reviewer}>
            <span>{item.reviewer}</span>
            <strong>{item.avgHours}h</strong>
          </li>
        ))}
      </ul>

      <h3>Bottlenecks</h3>
      <ul className="approval-list">
        {bottlenecks.length === 0 ? <li>No bottlenecks detected.</li> : null}
        {bottlenecks.map((request) => (
          <li key={request.id}>
            <span>{request.id}</span>
            <span>{request.title}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

