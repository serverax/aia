# Sprint 11 Technical Debt Register

Status: initial register
Owner: ChatGPT lane
Date: 2026-05-22

## Prioritization Rules

P0 items can block production confidence or expose secrets.
P1 items reduce operational risk during deployment.
P2 items improve maintainability but can defer if Sprint 11 capacity is tight.

## Debt Items

| ID | Priority | Area | Item | Why It Matters | Proposed Resolution | Owner |
|---|---:|---|---|---|---|---|
| TD-01 | P0 | Secrets | `monitoring-credentials.txt` appears untracked | credential-like files must not enter git | move to secret store or redact/delete locally after owner review | Ops/Security |
| TD-02 | P0 | CI/CD | live workflow execution not yet proven | Sprint 10 workflow definition is not release evidence | run blue-green workflow with Talos secret and attach artifact | ChatGPT/Ops |
| TD-03 | P0 | Evidence | Talos validation raw logs not yet attached to repo report | closure report depends on auditable evidence | attach operator logs to Sprint 10 release packet | Ops/ChatGPT |
| TD-04 | P1 | Traffic | backend does not guarantee blue/green response marker | traffic split cannot be measured precisely without color identity | add `x-deployment-color` header or `/version` endpoint | Gemini/Claude Code |
| TD-05 | P1 | Automation | traffic ramp script currently has local validation logic but not live HTTP sampler | ramp proof still depends on operator process | add sampler that sends 100 requests per stage | ChatGPT |
| TD-06 | P1 | Monitoring | canary-specific alerting not proven | bad canary could be missed until user impact | add canary latency/error/restart alerts | Ops |
| TD-07 | P1 | Flux | Flux reconcile evidence is not bundled automatically | release state may drift from git | add Flux status capture to evidence bundle | ChatGPT/Ops |
| TD-08 | P2 | Docs | namespace references exist across older `synthetic-enterprise` docs | old namespace can confuse operators | audit docs and add migration note where needed | ChatGPT |
| TD-09 | P2 | Repo Hygiene | unrelated dirty-tree files coexist with release work | increases accidental commit risk | isolate into owning branches or explicit commits | Lane owners |
| TD-10 | P2 | Shell Portability | shell scripts are validated by tests but not shellcheck in CI | syntax/portability issues can escape local Python tests | add shellcheck job or containerized script validation | ChatGPT/CI |

## Sprint 11 Allocation Recommendation

Reserve at least 25% of Sprint 11 capacity for P0/P1 debt:

- TD-01
- TD-02
- TD-03
- TD-04
- TD-05
- TD-06

## Review Cadence

Review this register:

- at Sprint 11 planning
- after CI workflow dry run
- after first live traffic ramp
- during Sprint 11 retrospective

## Closure Criteria

Each debt item must close with:

- owner
- remediation commit or evidence link
- validation command/output
- decision: closed, accepted risk, or deferred
