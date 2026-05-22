import { useEffect, useState } from 'react'
import {
  ApprovalDetail,
  ApprovalMetrics,
  ApprovalQueue,
  ApprovalRequestForm,
  AuditTrailTimeline,
} from '../components/Approval'
import { useApprovalAuditTrail } from '../hooks/useApprovalAuditTrail'
import { useApprovalDetail } from '../hooks/useApprovalDetail'
import { useApprovalMetrics } from '../hooks/useApprovalMetrics'
import { type ApprovalQueueFilter, useApprovalQueue } from '../hooks/useApprovalQueue'
import { useApprovalRequest } from '../hooks/useApprovalRequest'
import { approvalService } from '../services/approval/approvalService'
import type { ApprovalWorkflowRequest } from '../types/api'

interface ApprovalRequestPageProps {
  initialFilter?: ApprovalQueueFilter
}

export function ApprovalRequestPage({ initialFilter = 'waiting_me' }: ApprovalRequestPageProps) {
  const [explanationExpandedByRequest, setExplanationExpandedByRequest] = useState<Record<string, boolean>>({})
  const [confidenceAckByRequest, setConfidenceAckByRequest] = useState<Record<string, boolean>>({})
  const [selectedRequestIds, setSelectedRequestIds] = useState<string[]>([])
  const [isBulkSubmitting, setIsBulkSubmitting] = useState(false)
  const [bulkStatusMessage, setBulkStatusMessage] = useState<string | null>(null)
  const [undoExpiresAt, setUndoExpiresAt] = useState<number | null>(null)
  const [undoSecondsRemaining, setUndoSecondsRemaining] = useState(0)
  const [undoRestorePayload, setUndoRestorePayload] = useState<
    Array<{ id: string; status: 'pending' | 'in_progress' | 'approved' | 'rejected'; reviewers: ApprovalWorkflowRequest['reviewers']; feedback_thread: ApprovalWorkflowRequest['feedback_thread'] }>
  >([])
  const {
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
    outcomeFilter: queueOutcomeFilter,
    setOutcomeFilter: setQueueOutcomeFilter,
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
  } = useApprovalQueue(initialFilter)
  const { createRequest, isSubmitting, error } = useApprovalRequest()
  const {
    selectedRequestId,
    setSelectedRequestId,
    selectedRequest,
    feedbackDraft,
    setFeedbackDraft,
    statusMessage,
    isSubmittingDecision,
    submitDecision,
    escalate,
  } = useApprovalDetail(requests, currentReviewerId)
  const metrics = useApprovalMetrics(requests)
  const {
    events,
    isLoading: isAuditLoading,
    error: auditError,
    refresh: refreshAudit,
    agentFilter,
    setAgentFilter,
    policyFilter,
    setPolicyFilter,
    outcomeFilter: auditOutcomeFilter,
    setOutcomeFilter: setAuditOutcomeFilter,
    eventTypeFilter,
    setEventTypeFilter,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    agentOptions,
    policyOptions,
    retentionPolicy,
  } = useApprovalAuditTrail()

  const downloadText = (filename: string, text: string, type: string) => {
    const blob = new Blob([text], { type })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const exportAuditCsv = () => {
    const header = ['id', 'request_id', 'request_title', 'actor', 'outcome', 'policy', 'reason', 'timestamp'].join(
      ',',
    )
    const rows = events.map((event) =>
      [
        event.id,
        event.request_id,
        event.request_title,
        event.actor,
        event.outcome,
        event.policy,
        event.reason.replaceAll('"', '""'),
        event.timestamp,
      ]
        .map((value) => `"${String(value)}"`)
        .join(','),
    )
    downloadText(`audit-trail-${new Date().toISOString().slice(0, 10)}.csv`, [header, ...rows].join('\n'), 'text/csv')
  }

  const exportAuditJson = () => {
    downloadText(
      `audit-trail-${new Date().toISOString().slice(0, 10)}.json`,
      JSON.stringify(events, null, 2),
      'application/json',
    )
  }

  useEffect(() => {
    if (!selectedRequestId && filteredRequests.length > 0) {
      setSelectedRequestId(filteredRequests[0].id)
    }
  }, [filteredRequests, selectedRequestId, setSelectedRequestId])

  const handleCreate = async (input: Parameters<typeof createRequest>[0]) => {
    const created = await createRequest(input, currentReviewerId)
    await refresh()
    await refreshAudit()
    return created
  }

  const handleDecision = async (decision: 'approve' | 'reject', prefix?: string) => {
    if (selectedRequest?.recommendation_confidence.requires_acknowledgement && !confidenceAcknowledged) {
      return
    }
    const finalFeedback = prefix ? `${prefix}: ${feedbackDraft || 'No additional comment.'}` : feedbackDraft
    await submitDecision(decision, finalFeedback)
    setFeedbackDraft('')
    await refresh()
    await refreshAudit()
  }

  const handleEscalate = async () => {
    if (selectedRequest?.recommendation_confidence.requires_acknowledgement && !confidenceAcknowledged) {
      return
    }
    await escalate(feedbackDraft || 'No escalation reason provided.')
    setFeedbackDraft('')
    await refresh()
    await refreshAudit()
  }

  const handleBulkDecision = async (decision: 'approve' | 'reject') => {
    if (selectedRequestIds.length === 0) return
    const selectedSnapshots = requests
      .filter((request) => selectedRequestIds.includes(request.id))
      .map((request) => ({
        id: request.id,
        status: request.status,
        reviewers: request.reviewers,
        feedback_thread: request.feedback_thread,
      }))
    setUndoRestorePayload(selectedSnapshots)
    setIsBulkSubmitting(true)
    const result = await approvalService.submitBulkWorkflowDecision({
      requestIds: selectedRequestIds,
      reviewerId: currentReviewerId,
      decision,
      feedback: `Bulk ${decision} by ${currentReviewerId}`,
    })
    setIsBulkSubmitting(false)
    setBulkStatusMessage(
      `Bulk ${decision}: ${result.updatedCount} succeeded, ${result.failedCount} failed${result.failedIds.length ? ` (${result.failedIds.join(', ')})` : ''}.`,
    )
    setUndoExpiresAt(Date.now() + 30_000)
    setUndoSecondsRemaining(30)
    setSelectedRequestIds([])
    await refresh()
    await refreshAudit()
  }

  const handleBulkRequestChanges = async () => {
    if (selectedRequestIds.length === 0) return
    const selectedSnapshots = requests
      .filter((request) => selectedRequestIds.includes(request.id))
      .map((request) => ({
        id: request.id,
        status: request.status,
        reviewers: request.reviewers,
        feedback_thread: request.feedback_thread,
      }))
    setUndoRestorePayload(selectedSnapshots)
    setIsBulkSubmitting(true)
    const result = await approvalService.submitBulkWorkflowDecision({
      requestIds: selectedRequestIds,
      reviewerId: currentReviewerId,
      decision: 'request_changes',
      feedback: `Bulk request_changes by ${currentReviewerId}`,
    })
    setIsBulkSubmitting(false)
    setBulkStatusMessage(
      `Bulk request changes: ${result.updatedCount} succeeded, ${result.failedCount} failed${result.failedIds.length ? ` (${result.failedIds.join(', ')})` : ''}.`,
    )
    setUndoExpiresAt(Date.now() + 30_000)
    setUndoSecondsRemaining(30)
    setSelectedRequestIds([])
    await refresh()
    await refreshAudit()
  }

  const handleBulkEscalate = async () => {
    if (selectedRequestIds.length === 0) return
    const selectedSnapshots = requests
      .filter((request) => selectedRequestIds.includes(request.id))
      .map((request) => ({
        id: request.id,
        status: request.status,
        reviewers: request.reviewers,
        feedback_thread: request.feedback_thread,
      }))
    setUndoRestorePayload(selectedSnapshots)
    setIsBulkSubmitting(true)
    const result = await approvalService.escalateBulkWorkflow({
      requestIds: selectedRequestIds,
      reviewerId: currentReviewerId,
      reason: `Bulk escalation by ${currentReviewerId}`,
    })
    setIsBulkSubmitting(false)
    setBulkStatusMessage(
      `Bulk escalation: ${result.updatedCount} succeeded, ${result.failedCount} failed${result.failedIds.length ? ` (${result.failedIds.join(', ')})` : ''}.`,
    )
    setUndoExpiresAt(Date.now() + 30_000)
    setUndoSecondsRemaining(30)
    setSelectedRequestIds([])
    await refresh()
    await refreshAudit()
  }

  const handleUndoBulkAction = async () => {
    if (!undoExpiresAt || Date.now() > undoExpiresAt || undoRestorePayload.length === 0) return
    await approvalService.restoreBulkWorkflowState(undoRestorePayload)
    setUndoRestorePayload([])
    setUndoExpiresAt(null)
    setUndoSecondsRemaining(0)
    setBulkStatusMessage('Last bulk action was reverted.')
    await refresh()
    await refreshAudit()
  }

  useEffect(() => {
    if (!undoExpiresAt) return
    const timer = window.setInterval(() => {
      const remainingMs = undoExpiresAt - Date.now()
      if (remainingMs <= 0) {
        setUndoExpiresAt(null)
        setUndoSecondsRemaining(0)
        setUndoRestorePayload([])
        window.clearInterval(timer)
        return
      }
      setUndoSecondsRemaining(Math.ceil(remainingMs / 1000))
    }, 250)
    return () => window.clearInterval(timer)
  }, [undoExpiresAt])

  const explanationExpanded = selectedRequest
    ? Boolean(explanationExpandedByRequest[selectedRequest.id])
    : false
  const confidenceAcknowledged = selectedRequest ? Boolean(confidenceAckByRequest[selectedRequest.id]) : false
  const isGuardrailBlocked = Boolean(
    selectedRequest?.recommendation_confidence.requires_acknowledgement && !confidenceAcknowledged,
  )

  return (
    <main className="dashboard-layout">
      <header className="dashboard-header">
        <div>
          <h1>Approval Request UI</h1>
          <p>Manage approvals, reviewers, and SLA status in one place.</p>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {isLoading ? <p className="loading">Loading approval requests...</p> : null}

      <section className="approval-layout">
        <div className="approval-left">
          <ApprovalRequestForm onCreate={handleCreate} isSubmitting={isSubmitting} />
          <ApprovalQueue
            requests={filteredRequests}
            filter={filter}
            sortBy={sortBy}
            onFilterChange={setFilter}
            onSortByChange={setSortBy}
            onSelectRequest={setSelectedRequestId}
            selectedRequestIds={selectedRequestIds}
            onToggleRequestSelection={(requestId) => {
              setSelectedRequestIds((current) =>
                current.includes(requestId)
                  ? current.filter((item) => item !== requestId)
                  : [...current, requestId],
              )
            }}
            onToggleSelectAll={(checked) => {
              setSelectedRequestIds(checked ? filteredRequests.map((request) => request.id) : [])
            }}
            onBulkApprove={() => void handleBulkDecision('approve')}
            onBulkReject={() => void handleBulkDecision('reject')}
            onBulkRequestChanges={() => void handleBulkRequestChanges()}
            onBulkEscalate={() => void handleBulkEscalate()}
            isBulkSubmitting={isBulkSubmitting}
            bulkStatusMessage={bulkStatusMessage}
            undoSecondsRemaining={undoSecondsRemaining}
            onUndoBulkAction={() => void handleUndoBulkAction()}
            requestorQuery={requestorQuery}
            policyQuery={policyQuery}
            commentQuery={commentQuery}
            outcomeFilter={queueOutcomeFilter}
            statusFilter={statusFilter}
            assigneeQuery={assigneeQuery}
            requestIdQuery={requestIdQuery}
            slaFilter={slaFilter}
            templateFilter={templateFilter}
            dateFrom={dateFrom}
            dateTo={dateTo}
            onRequestorQueryChange={setRequestorQuery}
            onPolicyQueryChange={setPolicyQuery}
            onCommentQueryChange={setCommentQuery}
            onOutcomeFilterChange={setQueueOutcomeFilter}
            onStatusFilterChange={setStatusFilter}
            onAssigneeQueryChange={setAssigneeQuery}
            onRequestIdQueryChange={setRequestIdQuery}
            onSlaFilterChange={setSlaFilter}
            onTemplateFilterChange={setTemplateFilter}
            onDateFromChange={setDateFrom}
            onDateToChange={setDateTo}
            presets={presets}
            onApplyPreset={applyPreset}
            onSavePreset={saveCustomPreset}
            onDeletePreset={deletePreset}
          />
        </div>
        <div className="approval-right">
          <ApprovalMetrics
            avgCycleHours={metrics.avgCycleHours}
            slaComplianceRate={metrics.slaComplianceRate}
            reviewerRanking={metrics.reviewerRanking}
            bottlenecks={metrics.bottlenecks}
          />
          <ApprovalDetail
            request={selectedRequest ?? null}
            feedbackDraft={feedbackDraft}
            statusMessage={statusMessage}
            isSubmittingDecision={isSubmittingDecision}
            onFeedbackChange={setFeedbackDraft}
            onApprove={() => handleDecision('approve')}
            onRequestChanges={() => handleDecision('reject', 'Request changes')}
            onReject={() => handleDecision('reject')}
            onEscalate={handleEscalate}
            explanationExpanded={explanationExpanded}
            onToggleExplanation={() => {
              if (!selectedRequest) return
              setExplanationExpandedByRequest((current) => ({
                ...current,
                [selectedRequest.id]: !current[selectedRequest.id],
              }))
            }}
            confidenceAcknowledged={confidenceAcknowledged}
            onConfidenceAcknowledgedChange={(value) => {
              if (!selectedRequest) return
              setConfidenceAckByRequest((current) => ({
                ...current,
                [selectedRequest.id]: value,
              }))
            }}
            isGuardrailBlocked={isGuardrailBlocked}
          />
          <AuditTrailTimeline
            events={events}
            isLoading={isAuditLoading}
            error={auditError}
            agentFilter={agentFilter}
            policyFilter={policyFilter}
            outcomeFilter={auditOutcomeFilter}
            eventTypeFilter={eventTypeFilter}
            agentOptions={agentOptions}
            policyOptions={policyOptions}
            startDate={startDate}
            endDate={endDate}
            retentionPolicy={retentionPolicy}
            onAgentFilterChange={setAgentFilter}
            onPolicyFilterChange={setPolicyFilter}
            onOutcomeFilterChange={setAuditOutcomeFilter}
            onEventTypeFilterChange={setEventTypeFilter}
            onStartDateChange={setStartDate}
            onEndDateChange={setEndDate}
            onExportCsv={exportAuditCsv}
            onExportJson={exportAuditJson}
          />
        </div>
      </section>
    </main>
  )
}

