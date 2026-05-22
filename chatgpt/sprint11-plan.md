# Sprint 11 Planning

Status: draft planning package
Owner: ChatGPT lane
Date: 2026-05-22

## Sprint Goal

Turn the Sprint 10 blue-green deployment path into an operationally repeatable
production workflow with verified CI execution, monitoring coverage, evidence
capture, and reduced manual operator dependency.

## Planning Inputs

Sources:

- `chatgpt/SPRINT-10-CLOSURE-REPORT.md`
- `docs/BLUE-GREEN-DEPLOY.md`
- `.github/workflows/blue-green-deploy.yml`
- `docs/MONITORING-SETUP.md`
- `docs/OBSERVABILITY-RUNBOOKS.md`
- `docs/INCIDENT-RESPONSE-RUNBOOK.md`
- `docs/NETWORK-POLICY-TROUBLESHOOTING.md`
- current git status showing unrelated dirty-tree changes outside Sprint 10

## Proposed Sprint 11 Themes

### Theme 1: CI/CD Verification

Objective: prove the blue-green workflow in the live CI environment.

Candidate tasks:

- run `.github/workflows/blue-green-deploy.yml` with `run_apply=false`
- verify context assertion fails closed when context is wrong
- verify artifact upload for `reports/blue-green/`
- run gated apply with `run_apply=true` after operator approval
- document CI run IDs in the release record

Acceptance criteria:

- workflow completes successfully with Talos kubeconfig secret
- rollout gate output is captured as an artifact
- failed context check blocks the workflow
- no automatic apply occurs unless `run_apply=true`

### Theme 2: Monitoring and Alerting

Objective: make blue-green rollout health visible during and after release.

Candidate tasks:

- dashboard for canary p50/p95/p99 latency
- dashboard for blue vs green error rates
- alert on canary error rate above 1%
- alert on p95 latency above 3 seconds warning and 5 seconds critical
- alert on pod restarts during ramp
- capture ingress annotation state over time

Acceptance criteria:

- dashboard exists for live rollout
- alerts fire against test rules
- alert routing owner is documented
- rollback runbook links directly from alert description

### Theme 3: Evidence Automation

Objective: produce release-grade evidence without manual copy/paste.

Candidate tasks:

- create an evidence bundle script for Sprint 10/11 blue-green runs
- include context, nodes, namespace, rollout, endpoints, ingress, events, logs
- include CI run URL and artifact manifest
- include traffic ramp summary
- include rollback summary if rollback was tested

Acceptance criteria:

- one command creates a timestamped evidence bundle
- evidence bundle can be attached to stakeholder report
- generated bundle avoids secret leakage

### Theme 4: Traffic Ramp Hardening

Objective: validate real ingress traffic split, not only configuration.

Candidate tasks:

- add backend color marker endpoint or response header
- implement 100-request sample per ramp stage
- enforce +/- 2% tolerance only when enough requests are sampled
- record observed blue/green ratio
- stop and roll back automatically on ratio drift

Acceptance criteria:

- `0 -> 5 -> 25 -> 50 -> 100` ramp verified
- ratio output stored in evidence
- rollback triggers on tolerance failure

### Theme 5: Technical Debt and Cleanup

Objective: reduce release risk from unresolved repo and infrastructure drift.

Candidate tasks:

- isolate unrelated dirty-tree work into separate branch or commits
- resolve `.github/workflows/ci.yml` unrelated modification ownership
- review analyst-agent dirty files with owning lane
- move `monitoring-credentials.txt` out of repo or redact it
- standardize namespace naming across docs and scripts

Acceptance criteria:

- Sprint 11 worktree is clean for release paths
- credentials are not committed
- namespace naming is consistent
- ownership of non-ChatGPT dirty files is documented

## Proposed Sprint 11 Backlog

| ID | Work Item | Owner | Priority | Estimate | Acceptance |
|---|---|---|---:|---:|---|
| S11-01 | Run blue-green workflow in CI with `run_apply=false` | ChatGPT/Ops | P0 | 1d | workflow run artifact attached |
| S11-02 | Run gated apply in CI with operator approval | ChatGPT/Ops | P0 | 1d | apply succeeds or fails closed |
| S11-03 | Create blue-green evidence bundle script | ChatGPT | P0 | 1d | bundle includes context, rollout, endpoints, ingress, events |
| S11-04 | Add rollout monitoring dashboard | Ops/ChatGPT | P1 | 2d | canary latency and error rate visible |
| S11-05 | Add alert rules for canary failure | Ops | P1 | 1d | warning/critical routes tested |
| S11-06 | Add backend color marker for traffic sampling | Gemini/Claude Code | P1 | 2d | responses identify blue/green backend |
| S11-07 | Implement ingress traffic-ratio sampler | ChatGPT | P1 | 2d | 100 request samples report ratio |
| S11-08 | Run full traffic ramp e2e | ChatGPT/Ops | P0 | 1d | all stages pass or rollback evidence captured |
| S11-09 | Verify rollback from live canary state | ChatGPT/Ops | P0 | 1d | green weight returns to 0 and blue remains healthy |
| S11-10 | Clean or isolate unrelated dirty-tree changes | Owning lanes | P2 | 1d | release path clean |
| S11-11 | Remove/redact credential-like local files | Ops/Security | P0 | 0.5d | no plaintext credentials in repo |
| S11-12 | Update stakeholder report with Talos evidence | ChatGPT | P1 | 0.5d | report ready for presentation |

## Meeting Agenda

1. Confirm Sprint 10 closure evidence is attached.
2. Confirm Sprint 11 sprint goal.
3. Review P0 backlog items.
4. Confirm owners and dependencies.
5. Confirm CI secret availability.
6. Confirm monitoring owner and alert routing.
7. Confirm traffic marker strategy.
8. Confirm dirty-tree ownership.
9. Lock Sprint 11 scope and timeline.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| CI secret missing or wrong | workflow cannot run | Ops verifies `TALOS_KUBECONFIG` before sprint execution |
| Backend lacks color marker | traffic ratio cannot be proven | add marker endpoint/header as Sprint 11 P1 |
| Dirty tree overlaps release paths | accidental unrelated deployment changes | isolate branches and require scoped commits |
| Monitoring alerts not routed | failures may go unseen | test alert routing before ramp |
| Flux drift | rollout gate sees unexpected state | capture Flux reconcile status before apply |

## Definition of Done

Sprint 11 is complete when:

- CI workflow has at least one successful live run
- blue-green apply has live CI or operator evidence
- monitoring dashboard and alert thresholds are documented and tested
- traffic ramp has evidence for all stages or a documented rollback
- rollback path is executed and verified
- release evidence bundle is attached to stakeholder report
- dirty-tree release risks are owned or resolved
