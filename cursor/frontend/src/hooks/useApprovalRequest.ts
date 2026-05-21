import { useState } from 'react'
import { approvalService } from '../services/approval/approvalService'
import type { ApprovalWorkflowRequest, CreateApprovalWorkflowInput } from '../types/api'

export function useApprovalRequest() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createRequest = async (
    input: CreateApprovalWorkflowInput,
    requestor: string,
  ): Promise<ApprovalWorkflowRequest | null> => {
    setIsSubmitting(true)
    setError(null)
    try {
      return await approvalService.createRequest(input, requestor)
    } catch {
      setError('Unable to create approval request. Please retry.')
      return null
    } finally {
      setIsSubmitting(false)
    }
  }

  return {
    createRequest,
    isSubmitting,
    error,
  }
}

