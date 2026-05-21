import type { ApprovalFeedbackItem } from '../../types/api'

interface FeedbackThreadProps {
  items: ApprovalFeedbackItem[]
}

export function FeedbackThread({ items }: FeedbackThreadProps) {
  return (
    <section className="approval-thread">
      <h3>Feedback Thread</h3>
      <ul className="approval-list">
        {items.length === 0 ? <li>No feedback yet.</li> : null}
        {items.map((item) => (
          <li key={item.id}>
            <strong>{item.author}</strong>
            <p>{item.comment}</p>
            <small>{new Date(item.created_at).toLocaleString()}</small>
          </li>
        ))}
      </ul>
    </section>
  )
}

