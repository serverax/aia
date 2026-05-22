import type {
  ApprovalAuditEvent,
  ApprovalDecisionInput,
  ApprovalDecisionResult,
  ApprovalEscalationInput,
  ApprovalRequest,
  ApprovalWorkflowDecisionInput,
  ApprovalWorkflowRequest,
  CreateApprovalWorkflowInput,
  OrchestratorEventEnvelope,
  OrchestratorSnapshot,
} from './types'
import { MockOrchestratorClient } from './mock'

type EventHandler = (event: OrchestratorEventEnvelope) => void
type ConnectionHandler = (connected: boolean) => void

interface IOrchestratorClient {
  connect: () => void
  disconnect: () => void
  subscribe: (handler: EventHandler) => () => void
  subscribeConnection: (handler: ConnectionHandler) => () => void
  getSnapshot: () => Promise<OrchestratorSnapshot>
  getApprovals: () => Promise<ApprovalRequest[]>
  getApprovalWorkflows: () => Promise<ApprovalWorkflowRequest[]>
  getApprovalAuditTrail: (query?: { startDate?: string; endDate?: string }) => Promise<ApprovalAuditEvent[]>
  createApprovalWorkflow: (
    input: CreateApprovalWorkflowInput,
    requestor: string,
  ) => Promise<ApprovalWorkflowRequest>
  submitApprovalWorkflowDecision: (
    input: ApprovalWorkflowDecisionInput,
  ) => Promise<ApprovalWorkflowRequest | undefined>
  submitBulkApprovalWorkflowDecision: (input: {
    requestIds: string[]
    reviewerId: string
    decision: 'approve' | 'reject' | 'request_changes'
    feedback: string
  }) => Promise<{ updatedCount: number; failedCount: number; failedIds: string[] }>
  escalateApprovalWorkflow: (input: ApprovalEscalationInput) => Promise<ApprovalWorkflowRequest | undefined>
  escalateBulkApprovalWorkflow: (input: {
    requestIds: string[]
    reviewerId: string
    reason: string
  }) => Promise<{ updatedCount: number; failedCount: number; failedIds: string[] }>
  restoreBulkWorkflowState: (input: Array<{
    id: string
    status: ApprovalWorkflowRequest['status']
    reviewers: ApprovalWorkflowRequest['reviewers']
    feedback_thread: ApprovalWorkflowRequest['feedback_thread']
  }>) => Promise<void>
  submitApprovalDecision: (input: ApprovalDecisionInput) => Promise<ApprovalDecisionResult>
  debugSimulateDisconnect: () => void
}

class ApiOrchestratorClient implements IOrchestratorClient {
  private readonly socketUrl: string
  private readonly baseUrl: string
  private socket?: WebSocket
  private handlers: Set<EventHandler> = new Set()
  private connectionHandlers: Set<ConnectionHandler> = new Set()

  constructor() {
    this.socketUrl = import.meta.env.VITE_ORCHESTRATOR_WS_URL ?? 'ws://localhost:8080/ws'
    this.baseUrl = import.meta.env.VITE_ORCHESTRATOR_BASE_URL ?? 'http://localhost:8080'
  }

  connect() {
    if (this.socket && this.socket.readyState <= WebSocket.OPEN) return
    this.socket = new WebSocket(this.socketUrl)
    this.socket.onopen = () => this.emitConnection(true)
    this.socket.onmessage = (message) => {
      try {
        const parsed = JSON.parse(message.data) as OrchestratorEventEnvelope
        this.handlers.forEach((handler) => handler(parsed))
      } catch {
        // Ignore malformed payloads from unstable backend stubs.
      }
    }
    this.socket.onclose = () => this.emitConnection(false)
    this.socket.onerror = () => this.emitConnection(false)
  }

  disconnect() {
    this.socket?.close()
    this.socket = undefined
    this.emitConnection(false)
  }

  subscribe(handler: EventHandler) {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  subscribeConnection(handler: ConnectionHandler) {
    this.connectionHandlers.add(handler)
    return () => this.connectionHandlers.delete(handler)
  }

  async getSnapshot() {
    const response = await fetch(`${this.baseUrl}/api/v1/orchestrator/snapshot`)
    if (!response.ok) throw new Error('Failed to fetch orchestrator snapshot')
    return (await response.json()) as OrchestratorSnapshot
  }

  async getApprovals() {
    const response = await fetch(`${this.baseUrl}/api/v1/approvals`)
    if (!response.ok) return []
    return (await response.json()) as ApprovalRequest[]
  }

  async getApprovalWorkflows() {
    const response = await fetch(`${this.baseUrl}/api/v1/approval-requests`)
    if (!response.ok) return []
    return (await response.json()) as ApprovalWorkflowRequest[]
  }

  async getApprovalAuditTrail(query?: { startDate?: string; endDate?: string }) {
    const params = new URLSearchParams()
    if (query?.startDate) params.set('start_date', query.startDate)
    if (query?.endDate) params.set('end_date', query.endDate)
    const response = await fetch(`${this.baseUrl}/api/v1/approval-audit?${params.toString()}`)
    if (!response.ok) return []
    return (await response.json()) as ApprovalAuditEvent[]
  }

  async createApprovalWorkflow(input: CreateApprovalWorkflowInput, requestor: string) {
    const response = await fetch(`${this.baseUrl}/api/v1/approval-requests`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...input, requestor }),
    })
    if (!response.ok) throw new Error('Failed to create approval workflow')
    return (await response.json()) as ApprovalWorkflowRequest
  }

  async submitApprovalWorkflowDecision(input: ApprovalWorkflowDecisionInput) {
    const response = await fetch(`${this.baseUrl}/api/v1/approval-requests/${input.requestId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
    if (!response.ok) return undefined
    return (await response.json()) as ApprovalWorkflowRequest
  }

  async submitBulkApprovalWorkflowDecision(input: {
    requestIds: string[]
    reviewerId: string
    decision: 'approve' | 'reject' | 'request_changes'
    feedback: string
  }) {
    const response = await fetch(`${this.baseUrl}/api/v1/approval-requests/bulk-decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
    if (!response.ok) throw new Error('Failed to submit bulk workflow decision')
    return (await response.json()) as { updatedCount: number; failedCount: number; failedIds: string[] }
  }

  async escalateApprovalWorkflow(input: ApprovalEscalationInput) {
    const response = await fetch(`${this.baseUrl}/api/v1/approval-requests/${input.requestId}/escalate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
    if (!response.ok) return undefined
    return (await response.json()) as ApprovalWorkflowRequest
  }

  async escalateBulkApprovalWorkflow(input: {
    requestIds: string[]
    reviewerId: string
    reason: string
  }) {
    const response = await fetch(`${this.baseUrl}/api/v1/approval-requests/bulk-escalate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
    if (!response.ok) throw new Error('Failed to submit bulk escalation')
    return (await response.json()) as { updatedCount: number; failedCount: number; failedIds: string[] }
  }

  async restoreBulkWorkflowState(
    input: Array<{
      id: string
      status: ApprovalWorkflowRequest['status']
      reviewers: ApprovalWorkflowRequest['reviewers']
      feedback_thread: ApprovalWorkflowRequest['feedback_thread']
    }>,
  ) {
    await fetch(`${this.baseUrl}/api/v1/approval-requests/bulk-restore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: input }),
    })
  }

  async submitApprovalDecision(input: ApprovalDecisionInput) {
    const response = await fetch(`${this.baseUrl}/api/v1/approvals/${input.approvalId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })
    if (!response.ok) throw new Error('Failed to submit approval decision')
    return (await response.json()) as ApprovalDecisionResult
  }

  debugSimulateDisconnect() {
    this.disconnect()
  }

  private emitConnection(connected: boolean) {
    this.connectionHandlers.forEach((handler) => handler(connected))
  }
}

const mockClient = new MockOrchestratorClient()
const apiClient = new ApiOrchestratorClient()
const useMock = import.meta.env.VITE_ORCHESTRATOR_USE_MOCK !== 'false'

export const orchestratorClient: IOrchestratorClient = useMock
  ? {
      connect: () => mockClient.connect(),
      disconnect: () => mockClient.disconnect(),
      subscribe: (handler) => mockClient.subscribe(handler),
      subscribeConnection: (handler) => mockClient.subscribeConnection(handler),
      getSnapshot: () => mockClient.getSnapshot(),
      getApprovals: async () => mockClient.getApprovals(),
      getApprovalWorkflows: async () => mockClient.getApprovalWorkflows(),
      getApprovalAuditTrail: async (query) => mockClient.getApprovalAuditTrail(query),
      createApprovalWorkflow: async (input, requestor) => mockClient.createApprovalWorkflow(input, requestor),
      submitApprovalWorkflowDecision: async (input) => mockClient.submitApprovalWorkflowDecision(input),
      submitBulkApprovalWorkflowDecision: async (input) => mockClient.submitBulkApprovalWorkflowDecision(input),
      escalateApprovalWorkflow: async (input) => mockClient.escalateApprovalWorkflow(input),
      escalateBulkApprovalWorkflow: async (input) => mockClient.escalateBulkApprovalWorkflow(input),
      restoreBulkWorkflowState: async (input) => mockClient.restoreBulkWorkflowState(input),
      submitApprovalDecision: async (input) => mockClient.submitApprovalDecision(input),
      debugSimulateDisconnect: () => mockClient.debugSimulateDisconnect(),
    }
  : apiClient

export type { IOrchestratorClient }

