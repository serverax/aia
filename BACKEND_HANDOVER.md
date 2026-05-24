# BACKEND HANDOVER: Sprints 3, 4, 5

This document summarizes the backend services, API contracts, and integration points developed by the Gemini team.

## 🚀 Services Overview

| Service | Port | Description |
| :--- | :--- | :--- |
| **RAG System** | 8000 | Vector retrieval (Qdrant) + LLM context assembly. |
| **Analyst Agent** | 8001 | Decision reasoning, risk assessment, and HITL hub. |
| **Semantic Search** | 8002 | Semantic policy/guideline retrieval. |

## 🔗 Critical Endpoints for Integration

### For Cursor (Sprint 6 UI)

#### 1. Decision Explanation
- **Endpoint**: `POST /analyst/decision/explain`
- **Payload**: `{"query": "...", "decision_id": "..."}`
- **Returns**: `ExplanationPayload` (matched_policies, clause_rationale, decision_path).

#### 2. Confidence & Evaluation
- **Endpoint**: `POST /analyst/approval/evaluate`
- **Returns**: `ConfidenceScore` with multi-factor breakdown (low|medium|high bands).

#### 3. Real-Time Updates (HITL)
- **WebSocket**: `ws://<host>:8001/ws/hitl`
- **Events**: Broadcasts `{"type": "agent_step", "step": "...", "status": "..."}` as the analyst works.

#### 4. Document Preview & Audit
- **Preview**: `GET /analyst/document/preview?project_id=...` (returns HTML).
- **Audit**: `GET /analyst/document/audit/{doc_id}` (returns full draft history).

### For Claude Code (Sprint 6 Security)

- **Instrumentation**: All services use `libs.communication.telemetry` and are instrumented for OpenTelemetry.
- **Config**: Settings are centralized in `libs.communication.config.Config`.
- **WASM Readiness**: Analyst Agent is structured to support WASM tool execution (see `analyst_agent/main.py`).

### For ChatGPT (Sprint 8 Ops)

- **Performance Baseline**: `GEMINI_BASELINE_PERFORMANCE.md` contains P50/P95/P99 metrics.
- **Tuning**: `QDRANT_PERFORMANCE_TUNING.md` specifies production indexing parameters.

## 🛠️ Cluster Deployment Details

- **Deployment Strategy**: "Lite Production" (Public python:slim base + code injection).
- **Namespace**: `ordinox-ai`
- **Internal Hostnames**:
  - Redis: `redis.ordinox-ai:6379` (Running with emptyDir for validation)
  - Qdrant: `qdrant.data-layer:6333` (Running with Local PV on `cp1`)
- **Status**: Rollout in progress (installing dependencies).
- **Service URLs (Internal)**:
  - RAG: `http://rag-system.ordinox-ai:8000`
  - Analyst: `http://analyst-agent.ordinox-ai:8001` (Awaiting next pod spin-up)
  - Search: `http://semantic-search.ordinox-ai:8002`

---
**Status**: 🟢 Production Rollout Initiated | 🟡 Dependency Installation in Progress.
