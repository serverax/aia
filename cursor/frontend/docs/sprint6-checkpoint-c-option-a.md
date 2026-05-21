# Sprint 6 Checkpoint C (Option A): Advanced Filtering & Search

## 6.C.1 Multi-field search

Implemented in `ApprovalQueue` + `useApprovalQueue`:

- Requestor search (`request.requestor`)
- Date range search (`requested_at` and reviewer `signed_at` windows)
- Outcome filter (`approved`, `rejected`, `escalated`, `pending`)
- Policy search (`related_document_id` / request type fallback)
- Comment text search (feedback thread + explanation/confidence text)

## 6.C.2 Saved filter presets

Built-ins:

- My Pending Approvals
- Escalated Items
- Last 24 Hours
- High Confidence

Custom behaviors:

- Save current filter state as custom preset
- Delete custom preset
- Persist custom presets via `localStorage`

## Performance targets

Benchmarks include:

- search action latency
- filter action latency

Both are validated against `<500ms` threshold in `approval-benchmark.json`.
