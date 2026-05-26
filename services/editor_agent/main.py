"""Editor / Finalizer Agent consumer loop.

Mirrors ``services/echo_agent/main.py`` exactly for transport, audit and
tracing, so it behaves like every other specialist agent on the bus:

    consume(agent:editor:tasks) -> render -> publish(orchestrator:replies) -> ack

The task payload (``AgentMessage.data``) is expected to carry::

    {"title": str, "format": "md"|"docx"|"pdf", "sections": {field: value, ...}}

Rendering is delegated to an injectable ``renderer`` callable. The default
renderer produces Markdown bytes (no external deps); production wiring should
pass the existing ``cursor/services/editor_agent`` DOCX/PDF generator instead.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from contextlib import asynccontextmanager
from typing import Any, Callable

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

# renderer(payload) -> (bytes, mime_type)
Renderer = Callable[[dict[str, Any]], "tuple[bytes, str]"]


def render_markdown(payload: dict[str, Any]) -> tuple[bytes, str]:
    """Minimal, dependency-free default renderer.

    Replace at integration time with the real DOCX/PDF generator from
    ``cursor/services/editor_agent/generator``.
    """
    title = str(payload.get("title", "Untitled Document"))
    sections = payload.get("sections") or {}
    lines = [f"# {title}", ""]
    for field, value in sections.items():
        heading = str(field).replace("_", " ").title()
        lines.append(f"## {heading}")
        lines.append(str(value))
        lines.append("")
    return ("\n".join(lines)).encode("utf-8"), "text/markdown"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_id: str = "editor-v1"
    input_stream: str = "agent:editor:tasks"
    reply_stream: str = "orchestrator:replies"
    consumer_group: str = "editors"
    consumer_name: str = "editor-1"
    block_ms: int = 5000
    audit_enabled: bool = True
    otel_service_name: str = "editor"


settings = Settings()


class EditorAgent:
    """Consumer loop for document finalization tasks."""

    def __init__(self, settings: Settings, renderer: Renderer | None = None) -> None:
        self.settings = settings
        self.tracer = init_telemetry(service_name=settings.otel_service_name)
        self.redis = build_client()
        self.pg_pool = None
        self.renderer: Renderer = renderer or render_markdown
        self._stop = asyncio.Event()

    async def start_pg(self) -> None:
        if self.settings.audit_enabled:
            self.pg_pool = await build_pool()

    async def close(self) -> None:
        self._stop.set()
        await self.redis.close()
        if self.pg_pool:
            await self.pg_pool.close()

    async def run(self) -> None:
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

    def build_reply(self, incoming: AgentMessage) -> AgentMessage:
        """Pure transform: render the document and wrap it in a reply envelope.

        Factored out of `_handle` so it is unit-testable without Redis/Postgres.
        """
        artifact, mime = self.renderer(incoming.data)
        return AgentMessage(
            from_agent=self.settings.agent_id,
            to_agent=incoming.from_agent,
            task_id=incoming.task_id,
            message_type=MessageType.TASK_COMPLETE,
            status=MessageStatus.COMPLETED,
            data={
                "agent_id": self.settings.agent_id,
                "status": MessageStatus.COMPLETED.value,
                "mime_type": mime,
                "artifact_b64": base64.b64encode(artifact).decode("ascii"),
                "byte_length": len(artifact),
            },
            metadata={"in_reply_to": incoming.message_id, **incoming.metadata},
        )

    async def _handle(self, redis_id: str, fields: dict[str, str]) -> None:
        with self.tracer.start_as_current_span("editor.handle", kind=SpanKind.CONSUMER) as span:
            try:
                incoming = AgentMessage.from_stream_fields(fields)
                span.set_attribute("agent.task_id", incoming.task_id)
                await self._audit("in", incoming)

                reply = self.build_reply(incoming)
                await publish(self.redis, self.settings.reply_stream, reply.to_stream_fields())
                await self._audit("out", reply)
                await ack(
                    self.redis,
                    stream=self.settings.input_stream,
                    group=self.settings.consumer_group,
                    message_id=redis_id,
                )
                span.set_status(Status(StatusCode.OK))
            except Exception as exc:
                logger.exception("editor handling failed (redis_id=%s)", redis_id)
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))

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
            payload={"mime_type": message.data.get("mime_type")},
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent = EditorAgent(settings)
    await agent.start_pg()
    RedisInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()
    consumer_task = asyncio.create_task(agent.run(), name="editor-consumer")
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


app = FastAPI(title="Editor Agent", version="0.1.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    agent: EditorAgent = app.state.agent
    try:
        await agent.redis.ping()
    except Exception as exc:
        return {"status": "not_ready", "error": str(exc)}
    return {"status": "ready"}
