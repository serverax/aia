import { orchestratorClient } from '../orchestrator'
import type { ApprovalDecisionInput } from './types'

export const approvalService = {
  submitDecision(input: ApprovalDecisionInput) {
    return orchestratorClient.submitApprovalDecision(input)
  },
}

