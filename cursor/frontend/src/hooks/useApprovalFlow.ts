import { useState } from 'react'
import { approvalService } from '../services/approval/approvalService'

export function useApprovalFlow() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submitDecision = async (
    approvalId: string,
    decision: 'approve' | 'reject',
    reason: string,
    decidedBy: string,
  ) => {
    setIsSubmitting(true)
    setError(null)
    try {
      await approvalService.submitDecision({
        approvalId,
        decision,
        reason,
        decided_by: decidedBy,
      })
    } catch {
      setError('Unable to submit decision. Please retry.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return {
    submitDecision,
    isSubmitting,
    error,
  }
}

