import { useEffect, useMemo, useState } from 'react'
import { orchestratorClient } from '../services/orchestrator'
import type { ApprovalRequest, OrchestratorEventEnvelope, OrchestratorSnapshot } from '../types/api'

export function useWebSocket() {
  const [events, setEvents] = useState<OrchestratorEventEnvelope[]>([])
  const [snapshot, setSnapshot] = useState<OrchestratorSnapshot | null>(null)
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [reconnectAttempt, setReconnectAttempt] = useState(0)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true
    let reconnectTimeout: number | undefined

    const hydrateState = async () => {
      try {
        const [latestSnapshot, latestApprovals] = await Promise.all([
          orchestratorClient.getSnapshot(),
          orchestratorClient.getApprovals(),
        ])
        if (!isMounted) return
        setSnapshot(latestSnapshot)
        setApprovals(latestApprovals)
        setErrorMessage(null)
      } catch {
        if (!isMounted) return
        setErrorMessage('Unable to load live orchestrator state. Retrying connection...')
      }
    }

    const scheduleReconnect = (attempt: number) => {
      const delayMs = Math.min(1000 * 2 ** attempt, 8000)
      reconnectTimeout = window.setTimeout(() => {
        orchestratorClient.connect()
      }, delayMs)
    }

    orchestratorClient.connect()
    void hydrateState()

    const unsubscribeConnection = orchestratorClient.subscribeConnection((connected) => {
      if (!isMounted) return
      setIsConnected(connected)
      if (connected) {
        setReconnectAttempt(0)
        setErrorMessage(null)
        void hydrateState()
      } else {
        setReconnectAttempt((attempt) => {
          const nextAttempt = attempt + 1
          scheduleReconnect(nextAttempt)
          return nextAttempt
        })
      }
    })

    const unsubscribeEvents = orchestratorClient.subscribe((event) => {
      if (!isMounted) return
      setEvents((current) => [event, ...current].slice(0, 100))
      setErrorMessage(null)

      if (event.type === 'task_created') {
        const task = event.data as OrchestratorSnapshot['tasks'][number]
        setSnapshot((prev) =>
          prev
            ? {
                ...prev,
                tasks: [task, ...prev.tasks],
                last_update: event.timestamp,
              }
            : prev,
        )
      }

      if (event.type === 'task_updated') {
        const { task_id, status, progress } = event.data as {
          task_id: string
          status: OrchestratorSnapshot['tasks'][number]['status']
          progress?: number
        }
        setSnapshot((prev) =>
          prev
            ? {
                ...prev,
                tasks: prev.tasks.map((task) =>
                  task.id === task_id ? { ...task, status, progress } : task,
                ),
                last_update: event.timestamp,
              }
            : prev,
        )
      }

      if (event.type === 'approval_requested') {
        const data = event.data as { task_id: string; reason: string }
        setApprovals((current) => [
          {
            id: `approval_${Date.now()}`,
            taskId: data.task_id,
            title: 'Human approval required',
            summary: data.reason,
            requestedBy: 'orchestrator',
            createdAt: event.timestamp,
            status: 'pending',
          },
          ...current,
        ])
      }

      if (event.type === 'approval_decided') {
        const data = event.data as { approval_id: string; decision: 'approve' | 'reject' }
        setApprovals((current) =>
          current.map((approval) =>
            approval.id === data.approval_id ? { ...approval, status: data.decision } : approval,
          ),
        )
      }
    })

    return () => {
      isMounted = false
      if (reconnectTimeout) window.clearTimeout(reconnectTimeout)
      unsubscribeEvents()
      unsubscribeConnection()
      orchestratorClient.disconnect()
      setIsConnected(false)
    }
  }, [])

  const connectionLabel = useMemo(() => {
    if (isConnected) return 'Connected'
    if (reconnectAttempt > 0) return `Reconnecting (attempt ${reconnectAttempt})`
    return 'Disconnected'
  }, [isConnected, reconnectAttempt])

  return {
    snapshot,
    approvals,
    events,
    isConnected,
    connectionLabel,
    errorMessage,
    reconnectAttempt,
    retryConnection: () => {
      setErrorMessage(null)
      orchestratorClient.connect()
    },
    debugSimulateDisconnect: () => orchestratorClient.debugSimulateDisconnect(),
  }
}

