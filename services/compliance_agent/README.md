# Compliance Officer Agent

Sprint 2 skeleton. Receives task assignments from the Orchestrator on
`agent:compliance_officer:tasks`, runs deterministic keyword rules, and
publishes a `ComplianceResult` back on `orchestrator:replies`.

Co-located with `qdrant_indexer.py` (Sprint 3 — Gemini's RAG ingestion).
Sprint 3 swaps the placeholder `_evaluate()` in `main.py` for a real Qdrant
similarity search against UK legislation embeddings.

## Verdict rules (Sprint 2 placeholder)

| Trigger keywords | Verdict | Risk |
|---|---|---|
| violation, without consent, breach of contract, unauthorized transfer | REJECTED | RED |
| personal data, pii, third country, redundancy | REQUIRES_REVISION | AMBER |
| (no matches) | APPROVED | GREEN |

## Run locally

```
docker compose -f infrastructure/docker-compose.dev.yml up -d postgres redis jaeger
uvicorn services.compliance_agent.main:app --reload --port 8002
```

Then send it a task from an interactive Python shell:

```python
import asyncio
from libs.communication import AgentMessage, MessageStatus, MessageType
from libs.communication.redis_client import build_client, publish

async def main():
    client = build_client()
    msg = AgentMessage(
        from_agent="orchestrator-v1",
        to_agent="compliance_officer",
        task_id="t1",
        message_type=MessageType.TASK_ASSIGNMENT,
        status=MessageStatus.IN_PROGRESS,
        data={"description": "Process personal data without consent"},
    )
    await publish(client, "agent:compliance_officer:tasks", msg.to_stream_fields())
    await client.close()

asyncio.run(main())
```

Watch `XREAD COUNT 1 STREAMS orchestrator:replies 0`.
