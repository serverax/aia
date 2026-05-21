import type { ApprovalRequest } from './api'

export interface ApprovalState {
  pending: ApprovalRequest[]
  history: ApprovalRequest[]
}

