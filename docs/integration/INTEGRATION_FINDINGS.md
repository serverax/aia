# Integration Findings & Corrected Execution Plan

Produced during **safe local prep** (Option 1). Nothing was pushed, no history
rewritten, the live cluster was not touched. All work sits on the **local**
branch `feature/system-integration` (based on `claude/hiring-api` @ `51279b5`).

---

## 1. Branch conflict map (measured, read-only via `git merge-tree`)

Base for all = `origin/main` (merge-base `69f7bf9`).

| Branch | Result | What it brings | Notes |
|---|---|---|---|
| `chatgpt/realtime-collab` | ✅ **0 conflicts** | `services/realtime_collab/*` (manager, models, main, tests) — the missing WebSocket/HITL service | merged |
| `cursor/dashboard-ui` | ✅ **0 conflicts** | `cursor/frontend/*` dashboard + cross-browser evidence | merged |
| `gemini/user-auth-new` | ✅ **0 conflicts** | `libs/auth/*` (authenticate, middleware, models, security), wires orchestrator, adds `python-jose`+`passlib` to requirements | merged |
| `claude/structured-output-validation` | ❌ **~13 content conflicts** | structured-output work + `cursor/services/editor_agent/*` (real DOCX/PDF gen) + milvus/qdrant edits | **NOT merged** — stale (6 behind main); needs manual rebase |

**Correction to the original plan:** it predicted conflicts in `orchestrator/main.py` for the first three branches. In reality those three are **clean**; the only conflict-heavy branch is the stale `claude/structured-output-validation`.

### Conflicting files on the stale branch (for the human resolving it)
Content conflicts: `backend/waitlist/app.py`, `libs/llm/client.py`, `requirements.txt`,
`services/analyst_agent/analyst_service.py`, `services/analyst_agent/milvus_manager.py`,
`services/compliance_agent/qdrant_indexer.py`, `services/orchestrator_agent/main.py`,
`services/rag_system/rag_service.py`, `services/rag_system/rag_system.py`,
`services/semantic_search/api/main.py`, `services/semantic_search/vector_store/faiss_store.py`,
`services/tool_sandbox/tests/test_audit_adapter.py`, `tests/test_qdrant_indexer.py`.
Recommended: **rebase that branch onto current main first**, resolve there, then PR — do not merge as-is.

## 2. Discoveries that change the roadmap

1. **The Editor/Finalizer agent already exists** at `cursor/services/editor_agent/` (on the stale branch): `docx_generator.py`, `pdf_generator.py`, `markdown_to_html.py`, `schema_validator.py`, services + tests. Both the original plan and the first gap report wrongly called it "missing." **Do not build a new generator.** The only missing piece is event-bus transport → provided here as `services/editor_agent/main.py` (a thin Redis consumer that delegates to an injectable `renderer`; wire it to the existing generator at merge time).

2. **Auth already exists** (`gemini/user-auth-new`) and is now merged locally. After merge, `services/orchestrator_agent/main.py` hard-imports `libs.auth`, so the orchestrator now **requires `pip install -r requirements.txt`** (adds `python-jose[cryptography]==3.3.0`, `passlib[bcrypt]==1.7.4`). Without it, orchestrator import fails (`ModuleNotFoundError: jose`). This is a deploy/runtime prerequisite, not a bug.

3. **`services/analyst_agent/main.py` is real, correct, working code** and must **not** be overwritten (the original plan's Phase 1.4 would have destroyed it). The actual cleanup is removing the two duplicate implementations: `analyst_agent.py` (RAG class) and `analyst_service.py` (parallel FastAPI). Keep `main.py` as the canonical Redis consumer.

4. **Vector DB decision = Milvus** (per owner). `services/analyst_agent/milvus_manager.py` exists but is dead code; the canonical analyst path must be wired to it for per-tenant partition isolation. Qdrant/FAISS stacks in `rag_system`/`semantic_search` overlap and should be consolidated or scoped to the compliance corpus only.

5. **Fictional APIs in the original plan** (verified absent): `RedisClient`, `stream_consumer`, `emit_event`, `ComplianceClient`, `MessageType.TASK_ROUTE_ANALYST`. The real contracts are:
   - Redis: `libs.communication.redis_client.{build_client, consume, ack, publish}` (consumer groups; routing is via the `to_agent` field + per-agent stream names, not a special MessageType).
   - Messages: `libs.communication.AgentMessage` (`from_stream_fields`/`to_stream_fields`), enums `MessageType {TASK_ASSIGNMENT, TASK_COMPLETE, TASK_FAILED, HEARTBEAT, ESCALATION, ECHO}`, `MessageStatus`.
   - Kill-switch: `POST /compliance/evaluate` → `{allowed, reason, source, policy_version}`.

## 3. Code produced here (compiles, tests green)

| File | Purpose | Tests |
|---|---|---|
| `services/orchestrator_agent/compliance_gate.py` | `ComplianceGate.check()` — calls real `/compliance/evaluate`, injectable evaluator, **fail-closed** default | `tests/test_compliance_gate.py` (4 ✅) |
| `services/editor_agent/{__init__,main}.py` | Editor Redis-consumer transport, mirrors `echo_agent`, pluggable `renderer` | `tests/test_main.py` (3 ✅) |

`python -m pytest services/orchestrator_agent/tests/test_compliance_gate.py services/editor_agent/tests/test_main.py` → **7 passed**.
Merged-branch sanity: `services/realtime_collab/tests` (8 ✅), `services/orchestrator_agent/tests` excl. auth (18 ✅).

> The compliance gate is the *client*; it is **not yet wired** into the orchestrator's routing path. Wiring (call `gate.check(...)` before dispatch, reject on deny) is a reviewed follow-up, not done blind.

## 4. Corrected execution order (replaces the original phases)

1. **Rotate leaked credentials** (see `SECRET_INVENTORY_AND_SCRUB_RUNBOOK.md` §3 Step 0) — independent of everything, do now.
2. **Land integration** via reviewed PR from `feature/system-integration` (3 clean merges already staged). Add `pip install -r requirements.txt` to the orchestrator/auth deploy.
3. **Rebase + resolve `claude/structured-output-validation`**, then merge — this brings the real Editor generator + structured output. Wire `services/editor_agent/main.py` to it.
4. **Consolidate analyst**: delete `analyst_agent.py` + `analyst_service.py`; wire `main.py` → `milvus_manager.py` (Milvus per-tenant).
5. **Wire compliance gate** into orchestrator dispatch.
6. **Real determinism evals** (replace the mock in `libs/evaluation`).
7. **Helm charts + manifests** for analyst/rag/editor/tool-sandbox/realtime; fix CD (missing `scripts/compliance/*`), registry push.
8. **History scrub cutover** (runbook §3 Step 2–3) once all branches are merged.

## 5. Explicitly NOT done (needs authorization / a human operator)
- ❌ Any push / force-push / history rewrite.
- ❌ Any `kubectl`/`helm` against the live cluster.
- ❌ Credential rotation.
- ❌ Merging the stale conflict branch.
- ❌ Wiring the compliance gate into the live routing path.
