import { FeedbackThread } from './FeedbackThread'
import type { ApprovalWorkflowRequest } from '../../types/api'

interface ApprovalDetailProps {
  request: ApprovalWorkflowRequest | null
  feedbackDraft: string
  statusMessage: string | null
  isSubmittingDecision: boolean
  onFeedbackChange: (value: string) => void
  onApprove: () => void
  onRequestChanges: () => void
  onReject: () => void
  onEscalate: () => void
  explanationExpanded: boolean
  onToggleExplanation: () => void
  confidenceAcknowledged: boolean
  onConfidenceAcknowledgedChange: (value: boolean) => void
  isGuardrailBlocked: boolean
}

export function ApprovalDetail({
  request,
  feedbackDraft,
  statusMessage,
  isSubmittingDecision,
  onFeedbackChange,
  onApprove,
  onRequestChanges,
  onReject,
  onEscalate,
  explanationExpanded,
  onToggleExplanation,
  confidenceAcknowledged,
  onConfidenceAcknowledgedChange,
  isGuardrailBlocked,
}: ApprovalDetailProps) {
  const confidenceTitle = request
    ? request.recommendation_confidence.factors
        .map((factor) => `${factor.label} (${factor.impact}): ${factor.detail}`)
        .join('\n')
    : ''

  return (
    <section className="card approval-card">
      <h2>Approval Detail</h2>
      {!request ? <p>Select a request from the queue.</p> : null}

      {request ? (
        <>
          <div className="approval-detail-grid">
            <p>
              <strong>{request.title}</strong>
            </p>
            <p>Type: {request.request_type}</p>
            <p>Status: {request.status}</p>
            <p>Requester: {request.requestor}</p>
            <p>Requested at: {new Date(request.requested_at).toLocaleString()}</p>
            <p>Deadline: {new Date(request.deadline).toLocaleString()}</p>
            <p>Related document: {request.metadata.related_document_id ?? 'n/a'}</p>
            <p>Risk score: {request.metadata.risk_score ?? 'n/a'}</p>
            <p>
              Confidence:{' '}
              <span
                className={`pill confidence-${request.recommendation_confidence.band}`}
                title={confidenceTitle}
              >
                {request.recommendation_confidence.band} ({request.recommendation_confidence.score.toFixed(2)})
              </span>
            </p>
            <p>Description: {request.description}</p>
          </div>

          <button type="button" onClick={onToggleExplanation}>
            {explanationExpanded ? 'Hide' : 'Show'} Why this decision?
          </button>
          {explanationExpanded ? (
            <div className="decision-explanation">
              <p>{request.decision_explanation.summary}</p>
              <h4>Clause rationale</h4>
              <ul className="approval-list">
                {request.decision_explanation.clauses.map((clause) => (
                  <li key={clause.clause_id}>
                    <strong>{clause.title}</strong>
                    <span className={`pill ${clause.outcome}`}>{clause.outcome}</span>
                    <p>{clause.rationale}</p>
                    <small>Evidence: {clause.evidence}</small>
                  </li>
                ))}
              </ul>
              <h4>Decision path</h4>
              <ul className="decision-path">
                {request.decision_explanation.decision_path.map((step) => (
                  <li key={`${step.actor}-${step.timestamp}`}>
                    <strong>{step.actor}</strong> {step.action}
                    <p>{step.rationale}</p>
                    <small>{new Date(step.timestamp).toLocaleString()}</small>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {request.recommendation_confidence.requires_acknowledgement ? (
            <label className="guardrail-check">
              <input
                type="checkbox"
                checked={confidenceAcknowledged}
                onChange={(event) => onConfidenceAcknowledgedChange(event.target.checked)}
              />
              I acknowledge this is a low-confidence recommendation and accept manual review responsibility.
            </label>
          ) : null}
          {isGuardrailBlocked ? (
            <p className="error">Low-confidence guardrail: acknowledgement is required before decision submission.</p>
          ) : null}

          <h3>Reviewer Status</h3>
          <ul className="approval-list">
            {request.reviewers.map((reviewer) => (
              <li key={reviewer.user_id}>
                <strong>{reviewer.user_id}</strong>
                <span className={`pill ${reviewer.status}`}>{reviewer.status}</span>
                <p>{reviewer.feedback ?? 'No feedback yet.'}</p>
              </li>
            ))}
          </ul>

          <div className="approval-form-block">
            <label>Add feedback</label>
            <textarea
              value={feedbackDraft}
              rows={3}
              onChange={(event) => onFeedbackChange(event.target.value)}
              placeholder="Explain your decision"
            />
          </div>

          <div className="approval-actions">
            <button type="button" onClick={onApprove} disabled={isSubmittingDecision || isGuardrailBlocked}>
              Approve
            </button>
            <button type="button" onClick={onRequestChanges} disabled={isSubmittingDecision || isGuardrailBlocked}>
              Request Changes
            </button>
            <button
              type="button"
              className="danger"
              onClick={onReject}
              disabled={isSubmittingDecision || isGuardrailBlocked}
            >
              Reject
            </button>
            <button type="button" onClick={onEscalate} disabled={isSubmittingDecision || isGuardrailBlocked}>
              Escalate
            </button>
          </div>

          {statusMessage ? <p className="success">{statusMessage}</p> : null}
          <FeedbackThread items={request.feedback_thread} />
        </>
      ) : null}
    </section>
  )
}

