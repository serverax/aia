# Echo Agent

Sprint 1 proof-of-concept service. Consumes messages from a Redis Stream
and echoes them back, writing audit rows to Postgres and emitting OTLP
traces to Jaeger. Validates the full event-driven plumbing end-to-end.

## How it works

1. Reads `AgentMessage` envelopes from `agent:echo:tasks` via consumer group
   `echo-agents`.
2. For each message:
   - Starts an OpenTelemetry span.
   - Writes an `in` audit row to `audit_log`.
   - Publishes an `ECHO` reply on `agent:echo:results`.
   - Writes an `out` audit row.
   - `XACK`s the input.
3. Health (`/health`) and readiness (`/ready`) endpoints expose process and
   Redis status for kubelet probes.

## Config

All knobs are env vars; see `F:\aia\.env.example` for defaults.

| Var | Default | Purpose |
|---|---|---|
| `ECHO_INPUT_STREAM` | `agent:echo:tasks` | Stream consumed |
| `ECHO_OUTPUT_STREAM` | `agent:echo:results` | Stream produced |
| `ECHO_CONSUMER_GROUP` | `echo-agents` | Consumer group name |
| `ECHO_CONSUMER_NAME` | `echo-agent-1` | This instance's name |
| `REDIS_HOST`/`REDIS_PORT` | `localhost:6379` | Redis connection |
| `POSTGRES_*` | see `.env.example` | Audit log connection |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | none | Jaeger OTLP gRPC; falls back to console |

## Run locally

```
docker compose -f infrastructure/docker-compose.dev.yml up -d postgres redis jaeger
pip install -r services/echo_agent/requirements.txt
uvicorn services.echo_agent.main:app --reload --port 8000
```

Or run the full stack including the agent:

```
docker compose -f infrastructure/docker-compose.dev.yml up
```

## Send a test message

```python
import asyncio, json
from libs.communication import AgentMessage, MessageType, MessageStatus
from libs.communication.redis_client import build_client, publish

async def main():
    client = build_client()
    msg = AgentMessage(
        from_agent="test-rig",
        to_agent="echo-agent-v1",
        task_id="t1",
        message_type=MessageType.ECHO,
        status=MessageStatus.PENDING,
        data={"hello": "world"},
    )
    await publish(client, "agent:echo:tasks", msg.to_stream_fields())
    await client.close()

asyncio.run(main())
```

Then `XREAD COUNT 1 STREAMS agent:echo:results 0` in `redis-cli` to see the echo.
