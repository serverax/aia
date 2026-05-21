# Orchestrator Agent

Sprint 2's central service. Receives user requests, parses intent, decomposes
into atomic tasks, routes them to specialist agents over Redis Streams,
collects results, and either completes or escalates conflicts.

## Graph

```
intent_parser ─► should_continue ┬─► clarify ──────────────────► END
                                 │
                                 └─► task_decomposer
                                         │
                                         ▼
                                      router
                                         │
                                         ▼
                                      monitor
                                         │
                                         ▼
                                 conflict_resolver ─► conflict_branch
                                                            │
                                          ┌─────────────────┼─────────────────┐
                                          ▼                                   ▼
                                      complete ─► END                escalate ─► END
```

## Entry points

- **HTTP**: `POST /requests` with `{"user_request": "...", "project_id": "..."}`
- **Redis**: `XADD orchestrator:requests * request '{"user_request":"..."}'`

Both run the same graph; HTTP returns the terminal state synchronously.

## Streams

| Stream | Direction | Purpose |
|---|---|---|
| `orchestrator:requests` | in | external request submission |
| `agent:<type>:tasks` | out | per-agent task assignment |
| `orchestrator:replies` | in | aggregated agent results |
| `orchestrator:escalations` | out | conflicts requiring human review |

## Config

See `F:\aia\.env.example`. Critical env vars:

- `ANTHROPIC_API_KEY` — must be set in production; tests use `StubLLMClient`
- `ANTHROPIC_MODEL` — defaults to `claude-sonnet-4-6`
- `ORCHESTRATOR_MAX_CONCURRENT_DISPATCHES` — rate-limit semaphore (default 20)

## Run locally

```
docker compose -f infrastructure/docker-compose.dev.yml up -d postgres redis jaeger
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn services.orchestrator_agent.main:app --reload --port 8001
```

## Test without an API key

The unit tests inject `StubLLMClient` with canned responses, so they run
offline. The integration test does the same. See
`services/orchestrator_agent/tests/`.
