import { useState } from 'react'
import type { ApprovalRequest } from '../../types/api'

interface ApprovalModalProps {
  request: ApprovalRequest | null
  isSubmitting: boolean
  onClose: () => void
  onSubmit: (decision: 'approve' | 'reject', reason: string) => Promise<void>
}

export function ApprovalModal({ request, isSubmitting, onClose, onSubmit }: ApprovalModalProps) {
  const [reason, setReason] = useState('')

  if (!request) return null

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <section className="modal">
        <h3>{request.title}</h3>
        <p>{request.summary}</p>
        <textarea
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          placeholder="Decision reason"
          rows={4}
        />
        <div className="modal-actions">
          <button type="button" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onSubmit('reject', reason)}
            disabled={isSubmitting}
            className="danger"
          >
            Reject
          </button>
          <button
            type="button"
            onClick={() => onSubmit('approve', reason)}
            disabled={isSubmitting}
          >
            Approve
          </button>
        </div>
      </section>
    </div>
  )
}

