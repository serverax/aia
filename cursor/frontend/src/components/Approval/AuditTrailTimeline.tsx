import type { AuditOutcomeFilter } from '../../hooks/useApprovalAuditTrail'
import type { ApprovalAuditEvent } from '../../types/api'

interface AuditTrailTimelineProps {
  events: ApprovalAuditEvent[]
  isLoading: boolean
  error: string | null
  agentFilter: string
  policyFilter: string
  outcomeFilter: AuditOutcomeFilter
  agentOptions: string[]
  policyOptions: string[]
  onAgentFilterChange: (value: string) => void
  onPolicyFilterChange: (value: string) => void
  onOutcomeFilterChange: (value: AuditOutcomeFilter) => void
  startDate: string
  endDate: string
  retentionPolicy: {
    retentionDays: number
    archiveAfterDays: number
    purgeSchedule: string
  }
  onStartDateChange: (value: string) => void
  onEndDateChange: (value: string) => void
  onExportCsv: () => void
  onExportJson: () => void
}

export function AuditTrailTimeline({
  events,
  isLoading,
  error,
  agentFilter,
  policyFilter,
  outcomeFilter,
  agentOptions,
  policyOptions,
  onAgentFilterChange,
  onPolicyFilterChange,
  onOutcomeFilterChange,
  startDate,
  endDate,
  retentionPolicy,
  onStartDateChange,
  onEndDateChange,
  onExportCsv,
  onExportJson,
}: AuditTrailTimelineProps) {
  return (
    <section className="card approval-card">
      <h2>Audit Trail Timeline</h2>
      <div className="audit-filters">
        <select value={agentFilter} onChange={(event) => onAgentFilterChange(event.target.value)}>
          <option value="all">All agents</option>
          {agentOptions.map((agent) => (
            <option key={agent} value={agent}>
              {agent}
            </option>
          ))}
        </select>
        <select value={policyFilter} onChange={(event) => onPolicyFilterChange(event.target.value)}>
          <option value="all">All policies</option>
          {policyOptions.map((policy) => (
            <option key={policy} value={policy}>
              {policy}
            </option>
          ))}
        </select>
        <select
          value={outcomeFilter}
          onChange={(event) => onOutcomeFilterChange(event.target.value as AuditOutcomeFilter)}
        >
          <option value="all">All outcomes</option>
          <option value="approved">approved</option>
          <option value="rejected">rejected</option>
          <option value="overrode">overrode</option>
        </select>
      </div>
      <div className="audit-date-range">
        <label>
          Start date
          <input type="date" value={startDate} onChange={(event) => onStartDateChange(event.target.value)} />
        </label>
        <label>
          End date
          <input type="date" value={endDate} onChange={(event) => onEndDateChange(event.target.value)} />
        </label>
      </div>
      <div className="audit-export-row">
        <button type="button" onClick={onExportCsv}>
          Export CSV
        </button>
        <button type="button" onClick={onExportJson}>
          Export JSON
        </button>
      </div>

      <div className="audit-retention">
        <h3>Retention Policy</h3>
        <p>Events retained: {retentionPolicy.retentionDays} days</p>
        <p>Archive threshold: {retentionPolicy.archiveAfterDays} days</p>
        <p>Purge schedule: {retentionPolicy.purgeSchedule}</p>
      </div>

      {isLoading ? <p className="loading">Loading audit timeline...</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <ul className="audit-timeline">
        {events.map((event) => (
          <li key={event.id}>
            <div className="audit-head">
              <span className={`pill ${event.outcome}`}>{event.outcome}</span>
              <small>{new Date(event.timestamp).toLocaleString()}</small>
            </div>
            <p>
              <strong>{event.actor}</strong> on <strong>{event.request_title}</strong>
            </p>
            <p>Policy: {event.policy}</p>
            <p>Reason: {event.reason}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
