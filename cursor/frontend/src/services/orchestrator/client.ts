import type {
  ApprovalDecisionInput,
  ApprovalDecisionResult,
  ApprovalRequest,
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
  submitApprovalDecision: (input: ApprovalDecisionInput) => Promise<ApprovalDecisionResult>
  debugSimulateDisconnect: () => void
}

// Contract-compatible wrapper for the eventual Sprint 2 API.
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
        // Ignore malformed payloads until backend contract is finalized.
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
    if (!response.ok) {
      throw new Error('Failed to fetch orchestrator snapshot')
    }
    return (await response.json()) as OrchestratorSnapshot
  }

  async getApprovals() {
    const response = await fetch(`${this.baseUrl}/api/v1/approvals`)
    if (!response.ok) {
      return []
    }
    return (await response.json()) as ApprovalRequest[]
  }

  async submitApprovalDecision(input: ApprovalDecisionInput) {
    const response = await fetch(`${this.baseUrl}/api/v1/approvals/${input.approvalId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        decision: input.decision,
        reason: input.reason,
        decided_by: input.decided_by,
      }),
    })
    if (!response.ok) {
      throw new Error('Failed to submit approval decision')
    }
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
      submitApprovalDecision: (input) => mockClient.submitApprovalDecision(input),
      debugSimulateDisconnect: () => mockClient.debugSimulateDisconnect(),
    }
  : apiClient

export type { IOrchestratorClient }

