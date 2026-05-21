import type { ApprovalRequest } from '../../types/api'

interface ApprovalHistoryProps {
  pending: ApprovalRequest[]
  history: ApprovalRequest[]
  onOpenRequest: (request: ApprovalRequest) => void
}

export function ApprovalHistory({ pending, history, onOpenRequest }: ApprovalHistoryProps) {
  return (
    <section className="card">
      <h2>Approval Gate</h2>

      <h3>Pending</h3>
      {pending.length === 0 ? <p>No pending approvals.</p> : null}
      <ul className="approval-list">
        {pending.map((request) => (
          <li key={request.id}>
            <div>
              <strong>{request.title}</strong>
              <p>{request.summary}</p>
            </div>
            <button type="button" onClick={() => onOpenRequest(request)}>
              Review
            </button>
          </li>
        ))}
      </ul>

      <h3>Recent Decisions</h3>
      {history.length === 0 ? <p>No decisions yet.</p> : null}
      <ul className="approval-list">
        {history.slice(0, 5).map((request) => (
          <li key={request.id}>
            <span>{request.title}</span>
            <span className={`pill ${request.status}`}>{request.status}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

