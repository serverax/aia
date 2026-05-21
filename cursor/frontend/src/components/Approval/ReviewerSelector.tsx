import type { ApprovalStrategy } from '../../types/api'

interface ReviewerSelectorProps {
  reviewerInput: string
  reviewers: string[]
  deadline: string
  strategy: ApprovalStrategy
  onReviewerInputChange: (value: string) => void
  onAddReviewer: () => void
  onRemoveReviewer: (reviewer: string) => void
  onDeadlineChange: (value: string) => void
  onStrategyChange: (value: ApprovalStrategy) => void
}

export function ReviewerSelector({
  reviewerInput,
  reviewers,
  deadline,
  strategy,
  onReviewerInputChange,
  onAddReviewer,
  onRemoveReviewer,
  onDeadlineChange,
  onStrategyChange,
}: ReviewerSelectorProps) {
  return (
    <div className="approval-form-block">
      <label>Reviewers</label>
      <div className="reviewer-row">
        <input
          value={reviewerInput}
          onChange={(event) => onReviewerInputChange(event.target.value)}
          placeholder="reviewer@example.com"
        />
        <button type="button" onClick={onAddReviewer}>
          Add
        </button>
      </div>
      <ul className="reviewer-tags">
        {reviewers.map((reviewer) => (
          <li key={reviewer}>
            {reviewer}
            <button type="button" className="danger" onClick={() => onRemoveReviewer(reviewer)}>
              x
            </button>
          </li>
        ))}
      </ul>

      <label>Deadline</label>
      <input type="datetime-local" value={deadline} onChange={(event) => onDeadlineChange(event.target.value)} />

      <label>Approval Strategy</label>
      <select value={strategy} onChange={(event) => onStrategyChange(event.target.value as ApprovalStrategy)}>
        <option value="all_must_approve">all_must_approve</option>
        <option value="any_can_approve">any_can_approve</option>
        <option value="weighted_voting">weighted_voting</option>
      </select>
    </div>
  )
}

