"""Echo Agent: Sprint 1 proof-of-concept service.

Listens on a Redis Stream for AgentMessage envelopes and echoes the payload
back on a result stream. Each message is wrapped in an OpenTelemetry span
and written to the Postgres audit_log table on both ingress and egress.

The service intentionally does no application logic beyond echoing — its
role in Sprint 1 is to prove the full event-driven loop (Redis Streams +
consumer groups + Postgres audit + Jaeger traces) end to end.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.trace import SpanKind, Status, StatusCode
from pydantic_settings import BaseSettings, SettingsConfigDict

from libs.communication import AgentMessage, MessageStatus, MessageType
from libs.communication.postgres_client import audit, build_pool
from libs.communication.redis_client import ack, build_client, consume, publish
from libs.communication.telemetry import init_telemetry

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


class Settings(BaseSettings):
    """All knobs configurable via env vars (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_id: str = "echo-agent-v1"
    input_stream: str = "agent:echo:tasks"
    output_stream: str = "agent:echo:results"
    consumer_group: str = "echo-agents"
    consumer_name: str = "echo-agent-1"
    block_ms: int = 5000
    audit_enabled: bool = True
    otel_service_name: str = "echo-agent"


settings = Settings()


class EchoAgent:
    """The actual consumer loop. Holds clients for the service lifetime."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.tracer = init_telemetry(service_name=settings.otel_service_name)
        self.redis = build_client()
        self.pg_pool = None
        self._stop = asyncio.Event()

    async def start_pg(self) -> None:
        if self.settings.audit_enabled:
            self.pg_pool = await build_pool()
            logger.info("Postgres audit pool ready")

    async def close(self) -> None:
        self._stop.set()
        await self.redis.close()
        if self.pg_pool:
            await self.pg_pool.close()

    async def run(self) -> None:
        """Main consumer loop. Yields one message at a time."""
        logger.info(
            "Consuming stream=%s group=%s consumer=%s",
            self.settings.input_stream,
            self.settings.consumer_group,
            self.settings.consumer_name,
        )
        async for msg in consume(
            self.redis,
            stream=self.settings.input_stream,
            group=self.settings.consumer_group,
            consumer=self.settings.consumer_name,
            block_ms=self.settings.block_ms,
        ):
            if self._stop.is_set():
                break
            await self._handle(msg.message_id, msg.fields)

    async def _handle(self, redis_id: str, fields: dict[str, str]) -> None:
        with self.tracer.start_as_current_span(
            "echo_agent.handle_message", kind=SpanKind.CONSUMER
        ) as span:
            try:
                incoming = AgentMessage.from_stream_fields(fields)
                span.set_attribute("agent.message_id", incoming.message_id)
                span.set_attribute("agent.task_id", incoming.task_id)
                span.set_attribute("agent.from", incoming.from_agent)

                await self._audit("in", incoming)
                reply = self._build_echo(incoming)
                await publish(
                    self.redis,
                    stream=self.settings.output_stream,
                    fields=reply.to_stream_fields(),
                )
                await self._audit("out", reply)
                await ack(
                    self.redis,
                    stream=self.settings.input_stream,
                    group=self.settings.consumer_group,
                    message_id=redis_id,
                )
                span.set_status(Status(StatusCode.OK))
            except Exception as exc:
                logger.exception("Echo handling failed for redis_id=%s", redis_id)
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                # Leave unacked so it can be reclaimed by another consumer.

    def _build_echo(self, incoming: AgentMessage) -> AgentMessage:
        return AgentMessage(
            from_agent=self.settings.agent_id,
            to_agent=incoming.from_agent,
            task_id=incoming.task_id,
            message_type=MessageType.ECHO,
            status=MessageStatus.COMPLETED,
            data={"echoed": incoming.data, "received_at": incoming.timestamp},
            metadata={"in_reply_to": incoming.message_id},
        )

    async def _audit(self, direction: str, message: AgentMessage) -> None:
        if not (self.settings.audit_enabled and self.pg_pool):
            return
        await audit(
            self.pg_pool,
            agent_id=self.settings.agent_id,
            message_id=message.message_id,
            task_id=message.task_id,
            direction=direction,
            message_type=message.message_type.value,
            status=message.status.value,
            payload=message.data,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Boot the consumer loop alongside the FastAPI app."""
    agent = EchoAgent(settings)
    await agent.start_pg()

    # Auto-instrument transitively used libraries.
    RedisInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()

    consumer_task = asyncio.create_task(agent.run(), name="echo-consumer")
    app.state.agent = agent
    try:
        yield
    finally:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        await agent.close()


app = FastAPI(title="Echo Agent", version="0.1.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — always 200 once the process is up."""
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness probe — checks Redis is reachable."""
    agent: EchoAgent = app.state.agent
    try:
        await agent.redis.ping()
    except Exception as exc:
        return {"status": "not_ready", "error": str(exc)}
    return {"status": "ready"}
