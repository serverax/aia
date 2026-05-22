import { useEffect, useMemo, useState } from 'react'
import { approvalService } from '../services/approval/approvalService'
import type { ApprovalAuditEvent, ApprovalAuditOutcome } from '../types/api'

export type AuditOutcomeFilter = 'all' | ApprovalAuditOutcome
export type AuditEventTypeFilter = 'all' | 'decision' | 'bulk_action' | 'template' | 'undo'

export function useApprovalAuditTrail() {
  const [events, setEvents] = useState<ApprovalAuditEvent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [agentFilter, setAgentFilter] = useState('all')
  const [policyFilter, setPolicyFilter] = useState('all')
  const [outcomeFilter, setOutcomeFilter] = useState<AuditOutcomeFilter>('all')
  const [eventTypeFilter, setEventTypeFilter] = useState<AuditEventTypeFilter>('all')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const retentionPolicy = {
    retentionDays: 365,
    archiveAfterDays: 90,
    purgeSchedule: 'Monthly job on day 1',
  }

  const refresh = async (query?: { startDate?: string; endDate?: string }) => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await approvalService.listAuditTrail(query)
      setEvents(data)
    } catch {
      setError('Unable to load audit trail.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let mounted = true
    approvalService
      .listAuditTrail()
      .then((data) => {
        if (!mounted) return
        setEvents(data)
        setIsLoading(false)
      })
      .catch(() => {
        if (!mounted) return
        setError('Unable to load audit trail.')
        setIsLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true
    const start = startDate ? new Date(startDate).toISOString() : undefined
    const end = endDate ? new Date(`${endDate}T23:59:59.999Z`).toISOString() : undefined
    approvalService
      .listAuditTrail({ startDate: start, endDate: end })
      .then((data) => {
        if (!mounted) return
        setEvents(data)
        setIsLoading(false)
      })
      .catch(() => {
        if (!mounted) return
        setError('Unable to load audit trail.')
        setIsLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [startDate, endDate])

  const agentOptions = useMemo(() => Array.from(new Set(events.map((event) => event.actor))), [events])
  const policyOptions = useMemo(() => Array.from(new Set(events.map((event) => event.policy))), [events])

  const filteredEvents = useMemo(
    () =>
      events
        .filter((event) => (agentFilter === 'all' ? true : event.actor === agentFilter))
        .filter((event) => (policyFilter === 'all' ? true : event.policy === policyFilter))
        .filter((event) => (outcomeFilter === 'all' ? true : event.outcome === outcomeFilter))
        .filter((event) => (eventTypeFilter === 'all' ? true : event.event_type === eventTypeFilter))
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()),
    [agentFilter, eventTypeFilter, events, outcomeFilter, policyFilter],
  )

  return {
    events: filteredEvents,
    isLoading,
    error,
    refresh,
    agentFilter,
    setAgentFilter,
    policyFilter,
    setPolicyFilter,
    outcomeFilter,
    setOutcomeFilter,
    eventTypeFilter,
    setEventTypeFilter,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    agentOptions,
    policyOptions,
    retentionPolicy,
  }
}
