# Sprint 7 Compliance Controls

## Delivered Controls

- Kill-switch policy engine: `services/compliance-service/compliance_service/kill_switch.py`
- Compliance middleware: `services/compliance-service/compliance_service/middleware.py`
- Kill-switch API: `services/compliance-service/compliance_service/main.py`
- Tamper-evident audit hash-chain helpers: `services/compliance-service/compliance_service/audit_chain.py`
- Cluster manifests and policies: `infrastructure/compliance/`
- Sprint 7 test suite: `tests/compliance/`
- Cluster smoke script: `scripts/testing/sprint7_cluster_smoke.ps1`

## Operating Model

The kill switch supports four enforcement levels:

| Level | Control | Result |
| --- | --- | --- |
| Global | `global_enabled=true` | Blocks all non-exempt execution |
| Agent | `disabled_agents` | Blocks a named agent identity |
| Project | `disabled_projects` | Blocks work for a client/project |
| Capability | `disabled_capabilities` | Blocks sensitive actions such as external send |

The API returns a deterministic `policy_version` so every downstream decision can be logged and replayed.

## API

```http
GET /compliance/kill-switch
PUT /compliance/kill-switch
POST /compliance/evaluate
```

Example payload:

```json
{
  "global_enabled": true,
  "disabled_agents": [],
  "disabled_projects": [],
  "disabled_capabilities": ["external_send"],
  "reason": "Human compliance hold pending GDPR review",
  "updated_by": "human_compliance_team"
}
```

## Audit Integrity

`build_audit_hash()` hashes the previous row hash plus canonical row fields. `verify_audit_chain()` detects:

- inserted rows with a broken previous hash
- modified payloads or status fields
- deleted rows that break the chain

Production storage should persist `previous_hash` and `audit_hash` alongside each audit event.

## Acceptance Gate

Local tests validate deterministic control logic only. Sprint 7 approval requires the real Week 14-15 K3s cluster with all dependent services and databases deployed.

Run cluster smoke validation after deployment:

```powershell
.\scripts\testing\sprint7_cluster_smoke.ps1
```

## Current Cluster Runtime

The live cluster currently runs a temporary `python:3.11-alpine` ConfigMap-backed compliance API. This is intentional until the production image `ghcr.io/serverax/aia/compliance-service:latest` is either public or an `imagePullSecret` is configured. The placeholder runtime exposes `/health`, `/ready`, and `/compliance/evaluate` for Sprint 7 deployment validation, but it must be replaced by the packaged service image before production release.

Production follow-ups:

- Configure GHCR image pull authentication or publish the compliance-service image.
- Replace placeholder `llm-api-keys` value with the real Anthropic key.
- Deploy Vault and complete init/unseal.
- Fix `talosctl` CA/auth only when node-level management is required.
