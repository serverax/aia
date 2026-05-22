# Sprint 6 Checkpoint C Plan

## Objective
Deliver the next layer after Checkpoint B with production-safe traceability, operability, and decision intelligence.

Execution order:
1. Audit and compliance tracking
2. Advanced filtering and search
3. SLA visibility and alerts
4. Approval analytics dashboard

---

## Locked Requirements

### C.1 Audit and Compliance Tracking (Foundational)
- Log every bulk action event:
  - action type (`bulk_approve`, `bulk_reject`, `bulk_request_changes`, `bulk_escalate`)
  - actor (user id)
  - timestamp
  - selected request ids
  - success count / failed count / failed ids
  - reason/comment
  - latency (client-side measured)
- Log template events:
  - template selected
  - template preview viewed
  - template applied
  - fields auto-filled and SLA offset used
- Log undo events:
  - undo opened timestamp
  - undo executed/expired status
  - actor
  - restored request ids
  - restore outcome
- Persist logs to audit stream model used by `AuditTrailTimeline`.
- Add filters for event type and actor.
- Ensure event write latency target: `<100ms` per event in mock/contract path.

### C.2 Advanced Filtering and Search
- Add queue filters:
  - request status
  - assignee/reviewer
  - SLA urgency (`healthy`, `at_risk`, `breached`)
  - template type (`policy_standard`, `exception_fastlane`, `document_release`)
  - date range
- Add unified search by:
  - request id
  - title
  - description/comment content
  - related document id
- Keep saved preset compatibility with new filter fields.
- Performance target: 50 items filtered in `<500ms`.

### C.3 SLA Management and Alerts
- Compute SLA health from `deadline` and current time:
  - green: healthy
  - amber: approaching breach (configurable threshold, default 2h)
  - red: breached
- Surface SLA state in queue row, detail panel, and metrics widget.
- Add escalation suggestions when red state is reached.
- Add reminder hooks (UI signal now, notification integration later).

### C.4 Approval Analytics Dashboard
- Add metrics tiles/charts for:
  - throughput (approved/rejected per window)
  - average cycle time
  - escalation rate
  - template adoption rate
  - reviewer bottleneck ranking
- Provide date-range scoping and filter-aware metrics.
- Dashboard initial render target: `<2s`.

---

## Sprint Breakdown

## Sprint 6.5 (Critical Path)
Scope:
- C.1 Audit and compliance tracking
- C.2 Advanced filtering and search

Deliverables:
- Extended audit event model and logging in orchestrator mock + service
- Queue UI filter expansion + search-by-id/content
- Preset model migration for new filter fields
- Performance validation for event write + filter speed

Exit Criteria:
- All bulk/template/undo actions generate complete audit entries
- Event write latency `<100ms` (measured sample median)
- 50-item filter operation `<500ms`
- Lint/build/test green

## Sprint 6.6 (Operational + Insight)
Scope:
- C.3 SLA management and alerts
- C.4 Approval analytics dashboard

Deliverables:
- SLA urgency computation + visual states
- Alert cues and escalation guidance
- Analytics panel with required KPI set
- Dashboard load/perf instrumentation

Exit Criteria:
- SLA state visible in queue + detail + summary
- Dashboard load `<2s`
- KPI correctness verified against dataset
- Lint/build/test green

---

## Validation Matrix
- Audit write latency: `<100ms`
- Filter query latency (50 items): `<500ms`
- Dashboard load: `<2s`
- No regressions in Checkpoint B:
  - bulk 50 action `<2s`
  - template apply `<500ms`

---

## Immediate Execution Start
Begin Sprint 6.5 implementation now:
1. Extend audit event schema and log calls for bulk/template/undo.
2. Add status/assignee/SLA/template/date/request-id filters.
3. Update evidence scripts and benchmark outputs for C.1/C.2 gates.
