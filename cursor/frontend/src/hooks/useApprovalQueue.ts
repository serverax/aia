import { useEffect, useMemo, useState } from 'react'
import { approvalService } from '../services/approval/approvalService'
import type { ApprovalWorkflowRequest } from '../types/api'

export type ApprovalQueueFilter = 'waiting_me' | 'waiting_others' | 'completed'
export type QueueOutcomeFilter = 'all' | 'approved' | 'rejected' | 'escalated' | 'pending'
export type QueueStatusFilter = 'all' | 'pending' | 'in_progress' | 'approved' | 'rejected'
export type QueueSlaFilter = 'all' | 'healthy' | 'at_risk' | 'breached'

const currentReviewerId = 'you@synthetic.io'
const presetStorageKey = 'approval-queue-presets'

interface QueuePreset {
  id: string
  name: string
  requestorQuery: string
  policyQuery: string
  commentQuery: string
  outcomeFilter: QueueOutcomeFilter
  statusFilter: QueueStatusFilter
  assigneeQuery: string
  requestIdQuery: string
  slaFilter: QueueSlaFilter
  templateFilter: string
  dateFrom: string
  dateTo: string
  custom: boolean
}

const builtinPresets: QueuePreset[] = [
  {
    id: 'preset-my-pending',
    name: 'My Pending Approvals',
    requestorQuery: '',
    policyQuery: '',
    commentQuery: '',
    outcomeFilter: 'pending',
    statusFilter: 'all',
    assigneeQuery: '',
    requestIdQuery: '',
    slaFilter: 'all',
    templateFilter: 'all',
    dateFrom: '',
    dateTo: '',
    custom: false,
  },
  {
    id: 'preset-escalated',
    name: 'Escalated Items',
    requestorQuery: '',
    policyQuery: '',
    commentQuery: 'Escalated',
    outcomeFilter: 'escalated',
    statusFilter: 'all',
    assigneeQuery: '',
    requestIdQuery: '',
    slaFilter: 'all',
    templateFilter: 'all',
    dateFrom: '',
    dateTo: '',
    custom: false,
  },
  {
    id: 'preset-last-24h',
    name: 'Last 24 Hours',
    requestorQuery: '',
    policyQuery: '',
    commentQuery: '',
    outcomeFilter: 'all',
    statusFilter: 'all',
    assigneeQuery: '',
    requestIdQuery: '',
    slaFilter: 'all',
    templateFilter: 'all',
    dateFrom: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
    dateTo: new Date().toISOString().slice(0, 10),
    custom: false,
  },
  {
    id: 'preset-high-confidence',
    name: 'High Confidence',
    requestorQuery: '',
    policyQuery: '',
    commentQuery: 'positive',
    outcomeFilter: 'all',
    statusFilter: 'all',
    assigneeQuery: '',
    requestIdQuery: '',
    slaFilter: 'all',
    templateFilter: 'all',
    dateFrom: '',
    dateTo: '',
    custom: false,
  },
]

function isEscalated(request: ApprovalWorkflowRequest): boolean {
  return (
    request.feedback_thread.some((item) => item.comment.toLowerCase().includes('escalated')) ||
    request.decision_explanation.decision_path.some((step) => step.action.toLowerCase().includes('escalat'))
  )
}

function inDateRange(request: ApprovalWorkflowRequest, dateFrom: string, dateTo: string): boolean {
  if (!dateFrom && !dateTo) return true
  const requestMs = new Date(request.requested_at).getTime()
  const signedMs = request.reviewers
    .map((reviewer) => reviewer.signed_at)
    .filter((value): value is string => Boolean(value))
    .map((value) => new Date(value).getTime())
  const allTimes = [requestMs, ...signedMs]
  const fromMs = dateFrom ? new Date(`${dateFrom}T00:00:00.000Z`).getTime() : Number.MIN_SAFE_INTEGER
  const toMs = dateTo ? new Date(`${dateTo}T23:59:59.999Z`).getTime() : Number.MAX_SAFE_INTEGER
  return allTimes.some((value) => value >= fromMs && value <= toMs)
}

function slaUrgency(request: ApprovalWorkflowRequest): QueueSlaFilter {
  const delta = new Date(request.deadline).getTime() - Date.now()
  if (delta <= 0) return 'breached'
  if (delta <= 2 * 60 * 60 * 1000) return 'at_risk'
  return 'healthy'
}

export function useApprovalQueue(initialFilter: ApprovalQueueFilter = 'waiting_me') {
  const [requests, setRequests] = useState<ApprovalWorkflowRequest[]>([])
  const [filter, setFilter] = useState<ApprovalQueueFilter>(initialFilter)
  const [sortBy, setSortBy] = useState<'deadline' | 'risk' | 'requestor'>('deadline')
  const [isLoading, setIsLoading] = useState(true)
  const [requestorQuery, setRequestorQuery] = useState('')
  const [policyQuery, setPolicyQuery] = useState('')
  const [commentQuery, setCommentQuery] = useState('')
  const [outcomeFilter, setOutcomeFilter] = useState<QueueOutcomeFilter>('all')
  const [statusFilter, setStatusFilter] = useState<QueueStatusFilter>('all')
  const [assigneeQuery, setAssigneeQuery] = useState('')
  const [requestIdQuery, setRequestIdQuery] = useState('')
  const [slaFilter, setSlaFilter] = useState<QueueSlaFilter>('all')
  const [templateFilter, setTemplateFilter] = useState('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [customPresets, setCustomPresets] = useState<QueuePreset[]>(() => {
    try {
      const raw = localStorage.getItem(presetStorageKey)
      if (!raw) return []
      const parsed = JSON.parse(raw) as QueuePreset[]
      return parsed.filter((preset) => preset.custom)
    } catch {
      return []
    }
  })

  const refresh = async () => {
    setIsLoading(true)
    const data = await approvalService.listRequests()
    setRequests(data)
    setIsLoading(false)
  }

  useEffect(() => {
    let mounted = true
    approvalService.listRequests().then((data) => {
      if (!mounted) return
      setRequests(data)
      setIsLoading(false)
    })
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    localStorage.setItem(presetStorageKey, JSON.stringify(customPresets))
  }, [customPresets])

  const filteredRequests = useMemo(() => {
    const base = requests.filter((request) => {
      const myReviewer = request.reviewers.find((reviewer) => reviewer.user_id === currentReviewerId)
      if (filter === 'waiting_me') {
        return Boolean(myReviewer && myReviewer.status === 'pending')
      }
      if (filter === 'waiting_others') {
        return request.status === 'pending' || request.status === 'in_progress'
      }
      return request.status === 'approved' || request.status === 'rejected'
    })

    const searched = base
      .filter((request) =>
        requestorQuery
          ? request.requestor.toLowerCase().includes(requestorQuery.toLowerCase())
          : true,
      )
      .filter((request) =>
        policyQuery
          ? (request.metadata.related_document_id ?? request.request_type)
              .toLowerCase()
              .includes(policyQuery.toLowerCase())
          : true,
      )
      .filter((request) => {
        if (!commentQuery) return true
        const needle = commentQuery.toLowerCase()
        const feedbackMatch = request.feedback_thread.some((item) =>
          item.comment.toLowerCase().includes(needle),
        )
        const explanationMatch =
          request.decision_explanation.summary.toLowerCase().includes(needle) ||
          request.recommendation_confidence.factors.some((factor) =>
            `${factor.label} ${factor.detail}`.toLowerCase().includes(needle),
          )
        return feedbackMatch || explanationMatch
      })
      .filter((request) => {
        if (outcomeFilter === 'all') return true
        if (outcomeFilter === 'pending') return request.status === 'pending' || request.status === 'in_progress'
        if (outcomeFilter === 'escalated') return isEscalated(request)
        return request.status === outcomeFilter
      })
      .filter((request) => (statusFilter === 'all' ? true : request.status === statusFilter))
      .filter((request) =>
        assigneeQuery
          ? request.reviewers.some((reviewer) =>
              reviewer.user_id.toLowerCase().includes(assigneeQuery.toLowerCase()),
            )
          : true,
      )
      .filter((request) => {
        if (!requestIdQuery) return true
        const needle = requestIdQuery.toLowerCase()
        return (
          request.id.toLowerCase().includes(needle) ||
          request.title.toLowerCase().includes(needle) ||
          request.description.toLowerCase().includes(needle) ||
          (request.metadata.related_document_id ?? '').toLowerCase().includes(needle)
        )
      })
      .filter((request) => (slaFilter === 'all' ? true : slaUrgency(request) === slaFilter))
      .filter((request) =>
        templateFilter === 'all' ? true : (request.metadata.template_id ?? 'custom') === templateFilter,
      )
      .filter((request) => inDateRange(request, dateFrom, dateTo))

    return [...searched].sort((a, b) => {
      if (sortBy === 'requestor') return a.requestor.localeCompare(b.requestor)
      if (sortBy === 'risk') return (b.metadata.risk_score ?? 0) - (a.metadata.risk_score ?? 0)
      return new Date(a.deadline).getTime() - new Date(b.deadline).getTime()
    })
  }, [
    assigneeQuery,
    commentQuery,
    dateFrom,
    dateTo,
    filter,
    outcomeFilter,
    policyQuery,
    requestIdQuery,
    requestorQuery,
    requests,
    slaFilter,
    sortBy,
    statusFilter,
    templateFilter,
  ])

  const presets = useMemo(() => [...builtinPresets, ...customPresets], [customPresets])

  const applyPreset = (presetId: string) => {
    const preset = presets.find((item) => item.id === presetId)
    if (!preset) return
    setRequestorQuery(preset.requestorQuery)
    setPolicyQuery(preset.policyQuery)
    setCommentQuery(preset.commentQuery)
    setOutcomeFilter(preset.outcomeFilter)
    setStatusFilter(preset.statusFilter)
    setAssigneeQuery(preset.assigneeQuery)
    setRequestIdQuery(preset.requestIdQuery)
    setSlaFilter(preset.slaFilter)
    setTemplateFilter(preset.templateFilter)
    setDateFrom(preset.dateFrom)
    setDateTo(preset.dateTo)
  }

  const saveCustomPreset = (name: string) => {
    const normalized = name.trim()
    if (!normalized) return
    const next: QueuePreset = {
      id: `preset-custom-${Date.now()}`,
      name: normalized,
      requestorQuery,
      policyQuery,
      commentQuery,
      outcomeFilter,
      statusFilter,
      assigneeQuery,
      requestIdQuery,
      slaFilter,
      templateFilter,
      dateFrom,
      dateTo,
      custom: true,
    }
    setCustomPresets((current) => [next, ...current])
  }

  const deletePreset = (presetId: string) => {
    setCustomPresets((current) => current.filter((item) => item.id !== presetId))
  }

  return {
    requests,
    filteredRequests,
    filter,
    setFilter,
    sortBy,
    setSortBy,
    isLoading,
    refresh,
    currentReviewerId,
    requestorQuery,
    setRequestorQuery,
    policyQuery,
    setPolicyQuery,
    commentQuery,
    setCommentQuery,
    outcomeFilter,
    setOutcomeFilter,
    statusFilter,
    setStatusFilter,
    assigneeQuery,
    setAssigneeQuery,
    requestIdQuery,
    setRequestIdQuery,
    slaFilter,
    setSlaFilter,
    templateFilter,
    setTemplateFilter,
    dateFrom,
    setDateFrom,
    dateTo,
    setDateTo,
    presets,
    applyPreset,
    saveCustomPreset,
    deletePreset,
  }
}

