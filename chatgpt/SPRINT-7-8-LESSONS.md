# Sprint 7-8 Lessons and Watchpoints

## What Worked

- Sprint 7 was kept separate from Sprint 8, matching the approval cadence.
- Compliance controls were placed in `services/compliance-service`.
- Sprint 8 assets were prepared without executing production-only tests.
- Local tests validate deterministic logic while preserving the real-cluster acceptance gate.

## Week 14 Watchpoints

- Ask for explicit confirmation of the cluster starting state before running deployment checks.
- Confirm whether Sprint 1-6 resources are already running or whether the cluster is only partially staged.
- Confirm the Compliance Service image tag matches the deployed manifest.
- Confirm NetworkPolicies permit only intended in-cluster traffic.
- Confirm PostgreSQL audit schema is applied before compliance events are generated.
- Confirm the kill switch can block `external_send` without blocking health/readiness probes.
- Capture evidence from `scripts/testing/sprint7_cluster_smoke.ps1`.
- Keep `scripts/deployment/sprint7_rollback.ps1` ready before applying Sprint 7 manifests.

## Week 16 Watchpoints

- Load tests must run against the real ingress or production-equivalent endpoint.
- ZAP findings require human review before any exception is accepted.
- DR validation must measure actual RTO and RPO, not just execute commands.
- Blue-green validation must include rollback proof.

## Assumptions

- Sprint 1 provides K3s, PostgreSQL, Redis, and observability.
- Sprint 2 provides Orchestrator integration points.
- Sprint 3 provides Analyst and RAG services.
- Sprints 4-5 provide Frontend and Editor services.
- Sprint 6 provides WASM security controls.

## Troubleshooting Notes

- If `kubectl rollout status` hangs, inspect pod events and image pull status first.
- If smoke tests fail on port-forward, check service selectors and pod labels.
- If policy evaluation returns allowed unexpectedly, fetch `/compliance/kill-switch` and verify policy state.
- If audit verification fails after restore, stop release validation and escalate to the human compliance lead.
- If Sprint 7 deployment disrupts dependencies, run rollback first, then debug from the restored state.
