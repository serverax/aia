# Sprint 2 — Orchestrator + Compliance Officer

Weeks 3–4. Builds the central LangGraph-based Orchestrator that decomposes
user requests, dispatches per-agent tasks, monitors replies, and escalates
when the Compliance Officer vetoes.

## Deliverables (status)

| Deliverable | Status | Where |
|---|---|---|
| Orchestrator Agent (LangGraph) | Done | `services/orchestrator_agent/` |
| Intent parser | Done | `services/orchestrator_agent/nodes.py` |
| Task decomposer | Done | `services/orchestrator_agent/nodes.py` |
| Multi-agent router | Done | `services/orchestrator_agent/router.py` |
| Conflict detection + escalation | Done | `services/orchestrator_agent/conflict.py` |
| Rate limiting | Done | asyncio.Semaphore in router (env: `ORCHESTRATOR_MAX_CONCURRENT_DISPATCHES`) |
| Compliance Officer skeleton | Done | `services/compliance_agent/main.py` (rules: REJECTED/AMBER/APPROVED) |
| Compliance integration | Done | Orchestrator publishes to `agent:compliance_officer:tasks`; officer replies on `orchestrator:replies` |
| Audit logging | Done | `libs/communication/postgres_client.audit` called on both sides |
| Unit tests | Done | `services/orchestrator_agent/tests/*`, `services/compliance_agent/tests/*` |
| End-to-end integration test | Done | `tests/integration/test_orchestrator.py` |
| CI: build + push + deploy | Done | `.github/workflows/ci.yml` (lint → unit → integration → matrix build → deploy-staging) |

## File map (new in Sprint 2)

```
libs/
├── communication/message.py     # + ComplianceVerdict, RiskLevel, ComplianceResult
└── llm/                         # NEW
    ├── __init__.py
    └── client.py                # LLMClient Protocol, AnthropicClient, StubLLMClient

services/orchestrator_agent/     # NEW
├── state.py                     # TypedDict state for LangGraph
├── prompts.py                   # LLM templates
├── nodes.py                     # intent_parser, task_decomposer, conditional edges
├── router.py                    # Redis Streams dispatch + rate limit
├── monitor.py                   # Reply-stream tailing with timeout
├── conflict.py                  # detect_conflicts() + escalation publisher
├── graph.py                     # build_graph() wiring
├── main.py                      # FastAPI entry + background request consumer
├── Dockerfile / requirements.txt / README.md
└── tests/                       # test_nodes, test_conflict, test_router (fakeredis)

services/compliance_agent/
├── main.py                      # NEW — listener + _evaluate() rules
├── qdrant_indexer.py            # PRE-EXISTING (Sprint 3 — Gemini)
├── Dockerfile / requirements.txt / README.md
└── tests/test_main.py

infrastructure/k3s/
├── orchestrator-agent.yaml      # NEW
├── compliance-agent.yaml        # NEW
└── llm-secret.yaml              # NEW (template for ANTHROPIC_API_KEY)

infrastructure/docker-compose.dev.yml
                                 # + compliance-agent service (auto-started)
                                 # + orchestrator service (profile: with-llm)

.github/workflows/ci.yml         # rewritten: lint → unit → integration → build → deploy
```

## Run locally

### Unit tests only (fast, no docker)

```
pip install -r requirements-dev.txt
pytest tests/unit \
       services/echo_agent/tests \
       services/orchestrator_agent/tests \
       services/compliance_agent/tests \
       -m unit -v
```

### Integration test (docker stack — no API key needed)

```
docker compose -f infrastructure/docker-compose.dev.yml up -d \
    postgres redis jaeger compliance-agent echo-agent
pytest tests/integration -m integration -v
```

### Full stack with real orchestrator (LLM key required)

```
export ANTHROPIC_API_KEY=sk-ant-...
docker compose -f infrastructure/docker-compose.dev.yml --profile with-llm up

# Submit a request
curl -X POST http://localhost:8001/requests \
  -H 'content-type: application/json' \
  -d '{"user_request":"Draft a settlement agreement for disputed termination","project_id":"demo-1"}'
```

## Deploy to Hetzner

```
export KUBECONFIG=~/.kube/aia-config.yaml

# Set the API key (one-time)
kubectl create secret generic llm-api-keys \
  -n synthetic-enterprise \
  --from-literal=ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY

kubectl apply -f infrastructure/k3s/compliance-agent.yaml
kubectl apply -f infrastructure/k3s/orchestrator-agent.yaml

kubectl rollout status -n synthetic-enterprise deployment/orchestrator-agent
kubectl rollout status -n synthetic-enterprise deployment/compliance-agent
```

CI does this automatically on push to `main` if you set the `KUBECONFIG_STAGING` secret in the repo's GitHub Actions settings.

## Sprint 2 acceptance checklist

- [x] LangGraph compiles; `build_graph(llm=stub, redis_client=fake)` returns a compiled graph
- [x] Intent parser returns clarification path when LLM flags ambiguity
- [x] Task decomposer produces typed `TaskSpec`s with dependency edges
- [x] Router publishes to per-agent streams, respects `depends_on`, rate-limited
- [x] Monitor collects results from `orchestrator:replies` until all done or timeout
- [x] Conflict detector escalates on `ComplianceVerdict.REJECTED` or `RiskLevel.RED`
- [x] Escalation envelope published on `orchestrator:escalations`
- [x] Compliance Officer applies deterministic rules (Sprint 3 swaps for RAG)
- [x] Integration test exercises end-to-end veto path against real Redis + real Compliance Officer
- [x] CI: lint, unit, integration (with docker), matrix build to GHCR, gated deploy to staging
- [ ] **Hetzner cluster + manifests applied** (blocked: requires you to run `provision-cluster-full.sh` and apply manifests)
- [ ] **GitHub repo secrets configured** (`KUBECONFIG_STAGING`, optionally `ANTHROPIC_API_KEY`)

## Known gaps carried into Sprint 3

- `services/compliance_agent/_evaluate()` is keyword-based; Sprint 3 (Gemini)
  swaps in `qdrant_indexer.py` queries.
- Orchestrator scales to 1 replica only (monitor uses bare XREAD). Sprint 8
  hardening migrates monitor to consumer groups for HA.
- LLM debate loop from the original spec is not implemented — current
  conflict resolution is deterministic escalation. Add debate in Sprint 7
  if needed for the regulatory story.
- `langchain-anthropic` version (`0.2.1`) ships with `claude-sonnet-4-6`
  default; bump as Anthropic releases new model IDs.
