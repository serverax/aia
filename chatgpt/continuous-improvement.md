# Continuous Improvement Plan

Status: Sprint 11 operating plan
Owner: ChatGPT lane
Date: 2026-05-22

## Objective

Use the Sprint 10 blue-green deployment work to improve repeatability, evidence
quality, release confidence, and cross-lane coordination in Sprint 11.

## Retrospective Format

Run a short retrospective at the start and end of Sprint 11.

### Questions

1. What evidence prevented ambiguity?
2. What manual step slowed the team down?
3. What script or gate failed closed correctly?
4. What signal was missing from monitoring?
5. What dirty-tree or ownership issue created risk?
6. What should become a CI gate?

## Sprint 10 Observations

### Worked Well

- hard kube context gate prevented false Talos claims
- local deterministic tests caught logic issues before cluster execution
- rollback commands were embedded in both config and runbook
- Sprint 10 work stayed separated from unrelated dirty-tree changes

### Needs Improvement

- live CI workflow execution still needs proof
- raw Talos validation logs need a standard evidence bundle
- traffic ratio needs backend color markers
- multiple old namespace references remain in docs and scripts

## Sprint 11 Improvement Actions

| Action | Owner | Target |
|---|---|---|
| Add evidence bundle script for blue-green runs | ChatGPT | Week 1 |
| Verify live workflow and upload artifacts | Ops/ChatGPT | Week 1 |
| Add backend deployment color marker | Gemini/Claude Code | Week 1 |
| Add monitoring alerts for canary health | Ops | Week 2 |
| Audit namespace references | ChatGPT | Week 2 |
| Resolve credential-like local files | Ops/Security | Week 1 |

## Working Agreements

- Do not claim cluster success without raw operator output.
- Do not mix unrelated dirty-tree work with release automation.
- Treat context mismatch as a hard stop.
- Prefer evidence bundles over pasted summaries.
- Keep rollback commands adjacent to rollout commands.
- Capture Flux state before applying release resources.

## Process Metrics

Track during Sprint 11:

- time from operator evidence request to evidence delivery
- number of manual copy/paste steps
- number of failed gates caught before apply
- number of rollout-related alerts fired in test mode
- time to rollback from canary failure
- number of dirty-tree conflicts avoided by scoped commits

## Definition of Improvement

Sprint 11 improves the process if:

- CI produces a reusable blue-green evidence artifact
- canary monitoring is visible before ramp
- rollback can be triggered and verified in under 5 minutes
- release packet can be generated without manual log hunting
- stakeholders receive a single closure report with evidence links
