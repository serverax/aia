import { useMemo, useState } from 'react'
import { approvalService } from '../services/approval/approvalService'
import type { ApprovalWorkflowRequest } from '../types/api'

export function useApprovalDetail(requests: ApprovalWorkflowRequest[], reviewerId: string) {
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(requests[0]?.id ?? null)
  const [feedbackDraft, setFeedbackDraft] = useState('')
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false)

  const selectedRequest = useMemo(
    () => requests.find((request) => request.id === selectedRequestId),
    [requests, selectedRequestId],
  )

  const submitDecision = async (decision: 'approve' | 'reject', feedback: string) => {
    if (!selectedRequest) return null
    setIsSubmittingDecision(true)
    const updated = await approvalService.submitWorkflowDecision({
      requestId: selectedRequest.id,
      reviewerId,
      decision,
      feedback,
    })
    setIsSubmittingDecision(false)
    setStatusMessage(
      updated ? `Saved ${decision} decision for ${updated.id}.` : 'Unable to save decision.',
    )
    return updated
  }

  const escalate = async (reason: string) => {
    if (!selectedRequest) return null
    setIsSubmittingDecision(true)
    const updated = await approvalService.escalateWorkflow({
      requestId: selectedRequest.id,
      reviewerId,
      reason,
    })
    setIsSubmittingDecision(false)
    setStatusMessage(updated ? `Escalated ${updated.id} for compliance review.` : 'Unable to escalate request.')
    return updated
  }

  return {
    selectedRequestId,
    setSelectedRequestId,
    selectedRequest,
    feedbackDraft,
    setFeedbackDraft,
    statusMessage,
    isSubmittingDecision,
    submitDecision,
    escalate,
  }
}

