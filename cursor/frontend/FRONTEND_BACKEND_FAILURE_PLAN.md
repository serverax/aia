# Frontend-Backend Failure Plan

## Purpose

Define the rollback and degradation behavior when live backend integration fails during Talos execution or staging validation.

## Trigger Conditions

Activate this plan when any of the following occurs:

- Live `/evaluate` or `/api/v1/approval-requests` endpoint fails health/smoke checks.
- API responses are malformed (missing `decision_explanation` or `recommendation_confidence`).
- Backend latency exceeds acceptable thresholds for key flows.
- Repeated 5xx or timeout errors make approval actions unsafe.

## Immediate Frontend Response

1. **Preserve UX availability**
   - Keep Approval UI interactive in read mode.
   - Surface clear banner: "Live backend unavailable. Running in degraded mode."
2. **Disable risky writes**
   - Disable submit/reject/escalate and bulk actions until backend health recovers.
   - Keep export and historical timeline browsing enabled where safe.
3. **Fallback to mock mode for demos**
   - Set `VITE_ORCHESTRATOR_USE_MOCK=true`.
   - Restart frontend service.
4. **Capture incident evidence**
   - Save failing request/response snapshots.
   - Save `integration-live-backend-report.json`.

## Rollback Procedure

1. Repoint frontend to known-good mock:
   - `VITE_ORCHESTRATOR_USE_MOCK=true`
2. Restart app:
   - `npm run dev` or staging frontend deployment restart.
3. Verify fallback:
   - Dashboard/Approvals load without blocking errors.
   - Approval actions function against mock and audit updates continue.
4. Notify backend/deployment owners with captured evidence.

## Recovery Procedure (Return to Live Backend)

1. Run smoke test:
   - `npm run test:live-integration`
2. Confirm all checks pass:
   - evaluate status/shape
   - approvals status/shape
   - explanation/confidence presence
   - latency under threshold
3. Flip back to live:
   - `VITE_ORCHESTRATOR_USE_MOCK=false`
4. Re-run UI verification scripts:
   - `node scripts/approval-evidence.mjs`
   - `node scripts/approval-benchmark.mjs`

## Ownership

- Frontend owner: executes fallback and validates degraded mode.
- Backend owner: resolves API contract or availability issues.
- Ops owner: verifies cluster/network/service routing during Talos rollout.
