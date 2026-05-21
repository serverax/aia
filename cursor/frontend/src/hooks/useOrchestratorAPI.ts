import { useMemo } from 'react'
import { useWebSocket } from './useWebSocket'
import type { ApprovalRequest } from '../types/api'

export function useOrchestratorAPI() {
  const {
    snapshot,
    approvals,
    events,
    isConnected,
    connectionLabel,
    errorMessage,
    reconnectAttempt,
    retryConnection,
    debugSimulateDisconnect,
  } = useWebSocket()

  const pendingApprovals = useMemo(
    () => approvals.filter((approval) => approval.status === 'pending'),
    [approvals],
  )

  const approvalHistory = useMemo(
    () => approvals.filter((approval) => approval.status !== 'pending'),
    [approvals],
  )

  const findApprovalById = (approvalId: string): ApprovalRequest | undefined =>
    approvals.find((approval) => approval.id === approvalId)

  return {
    snapshot,
    events,
    isConnected,
    connectionLabel,
    errorMessage,
    reconnectAttempt,
    retryConnection,
    pendingApprovals,
    approvalHistory,
    findApprovalById,
    debugSimulateDisconnect,
  }
}

