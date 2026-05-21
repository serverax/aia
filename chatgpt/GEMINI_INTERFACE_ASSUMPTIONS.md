# Gemini Interface Assumptions

## Purpose

This document records the interface assumptions ChatGPT needs from Gemini before Sprint 8 load/security/DR testing expands beyond `compliance-service`.

## Request To Gemini Lane

Gemini, when you deploy the backend to Talos, please provide:

1. Service names and namespaces.
2. Health check endpoints.
3. Functional endpoints for evaluation/explanation.
4. Expected response-time targets.
5. Required environment variables.
6. Auth requirements for test calls.
7. Example request and response payloads.

## Current Assumptions

| Service | Assumed Namespace | Assumed Endpoint | Purpose | Target p95 |
| --- | --- | --- | --- | --- |
| analyst-agent | `synthetic-enterprise` | `/evaluate` | policy/domain evaluation | 1,500 ms |
| analyst-agent | `synthetic-enterprise` | `/explain` | confidence/source explanation | 2,000 ms |
| orchestrator | `synthetic-enterprise` | `/health` | orchestration readiness | 500 ms |
| compliance-service | `synthetic-enterprise` | `/compliance/evaluate` | compliance policy decision | 1,500 ms |

## Load Test Impact

The current Sprint 8 load profile only targets:

- `GET /health`
- `GET /ready`
- `POST /compliance/evaluate`

Gemini endpoints will be added only after Gemini confirms:

- service DNS name
- request schema
- response schema
- expected latency
- authentication mode

## Open Questions

- Is `/evaluate` synchronous or queued?
- Does `/explain` require source-document fixtures?
- Are confidence scores always present?
- What error shape is returned for invalid input?
- Is any endpoint rate-limited?

## Integration Gate

Do not add Gemini endpoints to the 1000-user Sprint 8 production target until a 10-user baseline passes with:

- error rate below `0.1%`
- p95 under Gemini-provided target
- no pod restarts
- response schema matches documented contract
