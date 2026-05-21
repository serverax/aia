# Sprint 5.4 Audit Export and Retention Strategy

## Export capabilities

Audit timeline exports are available directly in the UI:

- **Export CSV** for spreadsheet/compliance handoff
- **Export JSON** for downstream ingestion and forensic tooling

Exports always use the currently filtered timeline view (agent/policy/outcome/date range).

## Date-range query behavior

Timeline supports query window controls:

- `startDate` (inclusive)
- `endDate` (inclusive to end-of-day)

The query is passed to the audit API contract as:

- `start_date` (ISO8601)
- `end_date` (ISO8601)

## Retention policy display (UI)

Displayed in timeline panel:

- Retain events: **365 days**
- Archive threshold: **90 days**
- Purge schedule: **Monthly job on day 1**

## Archive and purge strategy

1. **Hot store (0-90 days)**
   - Queryable for UI timeline and operational reviews.
2. **Archive tier (91-365 days)**
   - Moved to low-cost immutable object storage as compressed JSONL partitions.
3. **Purge stage (>365 days)**
   - Monthly purge process removes expired records from hot/archive indexes.
4. **Compliance override path**
   - Legal hold flag excludes selected events/requests from purge until hold is lifted.

## Operational notes

- Export actions are client-side and do not mutate server state.
- Retention settings are displayed in UI for transparency; enforcement is expected in backend jobs.
