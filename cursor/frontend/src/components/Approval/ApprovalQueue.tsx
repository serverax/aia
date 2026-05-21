import { useState } from 'react'
import type { ApprovalQueueFilter, QueueOutcomeFilter } from '../../hooks/useApprovalQueue'
import type { ApprovalWorkflowRequest } from '../../types/api'

interface ApprovalQueueProps {
  requests: ApprovalWorkflowRequest[]
  filter: ApprovalQueueFilter
  sortBy: 'deadline' | 'risk' | 'requestor'
  onFilterChange: (value: ApprovalQueueFilter) => void
  onSortByChange: (value: 'deadline' | 'risk' | 'requestor') => void
  onSelectRequest: (requestId: string) => void
  selectedRequestIds: string[]
  onToggleRequestSelection: (requestId: string) => void
  onToggleSelectAll: (checked: boolean) => void
  onBulkApprove: () => void
  onBulkReject: () => void
  onBulkEscalate: () => void
  isBulkSubmitting: boolean
  bulkStatusMessage: string | null
  requestorQuery: string
  policyQuery: string
  commentQuery: string
  outcomeFilter: QueueOutcomeFilter
  dateFrom: string
  dateTo: string
  onRequestorQueryChange: (value: string) => void
  onPolicyQueryChange: (value: string) => void
  onCommentQueryChange: (value: string) => void
  onOutcomeFilterChange: (value: QueueOutcomeFilter) => void
  onDateFromChange: (value: string) => void
  onDateToChange: (value: string) => void
  presets: Array<{ id: string; name: string; custom: boolean }>
  onApplyPreset: (presetId: string) => void
  onSavePreset: (name: string) => void
  onDeletePreset: (presetId: string) => void
}

export function ApprovalQueue({
  requests,
  filter,
  sortBy,
  onFilterChange,
  onSortByChange,
  onSelectRequest,
  selectedRequestIds,
  onToggleRequestSelection,
  onToggleSelectAll,
  onBulkApprove,
  onBulkReject,
  onBulkEscalate,
  isBulkSubmitting,
  bulkStatusMessage,
  requestorQuery,
  policyQuery,
  commentQuery,
  outcomeFilter,
  dateFrom,
  dateTo,
  onRequestorQueryChange,
  onPolicyQueryChange,
  onCommentQueryChange,
  onOutcomeFilterChange,
  onDateFromChange,
  onDateToChange,
  presets,
  onApplyPreset,
  onSavePreset,
  onDeletePreset,
}: ApprovalQueueProps) {
  const [presetNameDraft, setPresetNameDraft] = useState('')
  const allVisibleSelected = requests.length > 0 && requests.every((request) => selectedRequestIds.includes(request.id))

  return (
    <section className="card approval-card">
      <h2>Approval Queue</h2>
      <div className="approval-queue-controls">
        <select value={filter} onChange={(event) => onFilterChange(event.target.value as ApprovalQueueFilter)}>
          <option value="waiting_me">Waiting for me</option>
          <option value="waiting_others">Waiting for others</option>
          <option value="completed">Completed</option>
        </select>
        <select value={sortBy} onChange={(event) => onSortByChange(event.target.value as 'deadline' | 'risk' | 'requestor')}>
          <option value="deadline">Sort by deadline</option>
          <option value="risk">Sort by risk</option>
          <option value="requestor">Sort by requester</option>
        </select>
        <label className="bulk-select-all">
          <input
            type="checkbox"
            checked={allVisibleSelected}
            onChange={(event) => onToggleSelectAll(event.target.checked)}
          />
          Select all visible
        </label>
      </div>
      <div className="approval-bulk-bar">
        <span>{selectedRequestIds.length} selected</span>
        <div className="approval-bulk-actions">
          <button type="button" onClick={onBulkApprove} disabled={isBulkSubmitting || selectedRequestIds.length === 0}>
            Bulk Approve
          </button>
          <button type="button" onClick={onBulkReject} disabled={isBulkSubmitting || selectedRequestIds.length === 0}>
            Bulk Reject
          </button>
          <button type="button" onClick={onBulkEscalate} disabled={isBulkSubmitting || selectedRequestIds.length === 0}>
            Bulk Escalate
          </button>
        </div>
      </div>
      {bulkStatusMessage ? <p className="success">{bulkStatusMessage}</p> : null}

      <div className="approval-search-grid">
        <input
          placeholder="Search requestor"
          value={requestorQuery}
          onChange={(event) => onRequestorQueryChange(event.target.value)}
        />
        <input
          placeholder="Search policy ID/name"
          value={policyQuery}
          onChange={(event) => onPolicyQueryChange(event.target.value)}
        />
        <input
          placeholder="Search comments/text"
          value={commentQuery}
          onChange={(event) => onCommentQueryChange(event.target.value)}
        />
        <select
          value={outcomeFilter}
          onChange={(event) => onOutcomeFilterChange(event.target.value as QueueOutcomeFilter)}
        >
          <option value="all">All outcomes</option>
          <option value="approved">approved</option>
          <option value="rejected">rejected</option>
          <option value="escalated">escalated</option>
          <option value="pending">pending</option>
        </select>
        <input type="date" value={dateFrom} onChange={(event) => onDateFromChange(event.target.value)} />
        <input type="date" value={dateTo} onChange={(event) => onDateToChange(event.target.value)} />
      </div>

      <div className="approval-presets">
        <div className="preset-actions">
          <input
            placeholder="Preset name"
            value={presetNameDraft}
            onChange={(event) => setPresetNameDraft(event.target.value)}
          />
          <button
            type="button"
            onClick={() => {
              onSavePreset(presetNameDraft)
              setPresetNameDraft('')
            }}
          >
            Save Preset
          </button>
        </div>
        <ul className="preset-list">
          {presets.map((preset) => (
            <li key={preset.id}>
              <button type="button" onClick={() => onApplyPreset(preset.id)}>
                {preset.name}
              </button>
              {preset.custom ? (
                <button type="button" className="danger" onClick={() => onDeletePreset(preset.id)}>
                  Delete
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      </div>

      <ul className="approval-list">
        {requests.map((request) => {
          const approved = request.reviewers.filter((reviewer) => reviewer.status === 'approved').length
          return (
            <li key={request.id} className="approval-queue-row">
              <div>
                <label className="approval-row-select">
                  <input
                    type="checkbox"
                    checked={selectedRequestIds.includes(request.id)}
                    onChange={() => onToggleRequestSelection(request.id)}
                  />
                </label>
                <strong>{request.title}</strong>
                <p>
                  {request.request_type} | {request.requestor}
                </p>
                <small>
                  Progress: {approved}/{request.reviewers.length} approved
                </small>
              </div>
              <div className="approval-queue-actions">
                <span className={`pill ${request.status}`}>{request.status}</span>
                <button type="button" onClick={() => onSelectRequest(request.id)}>
                  Open
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

