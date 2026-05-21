"""Compliance Officer Agent — Sprint 2 skeleton.

Listens on `agent:compliance_officer:tasks`, reviews each task with a
deterministic keyword check (placeholder for Sprint 3's Qdrant-backed RAG
lookup via `qdrant_indexer.py`), and publishes a `ComplianceResult` back to
`orchestrator:replies`. Audits ingress + egress to Postgres.

Replace `_evaluate()` in Sprint 3 with a real call into `QdrantIndexer.search()`.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.trace import SpanKind, Status, StatusCode
from pydantic_settings import BaseSettings, SettingsConfigDict

from libs.communication import (
    AgentMessage,
    ComplianceResult,
    ComplianceVerdict,
    MessageStatus,
    MessageType,
    RiskLevel,
)
from libs.communication.postgres_client import audit, build_pool
from libs.communication.redis_client import ack, build_client, consume, publish
from libs.communication.telemetry import init_telemetry

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_id: str = "compliance-officer-v1"
    input_stream: str = "agent:compliance_officer:tasks"
    reply_stream: str = "orchestrator:replies"
    consumer_group: str = "compliance-officers"
    consumer_name: str = "compliance-officer-1"
    audit_enabled: bool = True
    otel_service_name: str = "compliance-officer"


settings = Settings()


# Placeholder rules. Sprint 3 replaces with Qdrant-backed similarity search
# over UK legislation + SRA guidance.
_REJECT_KEYWORDS = ("violation", "without consent", "breach of contract", "unauthorized transfer")
_AMBER_KEYWORDS = ("personal data", "pii", "third country", "redundancy")


def _evaluate(description: str, inputs: dict[str, Any]) -> ComplianceResult:
    """Deterministic verdict from a task description + inputs.

    The integration test relies on these rules being predictable. Keep
    deterministic until Sprint 3 swaps in RAG.
    """
    haystack = " ".join([description, *map(str, inputs.values())]).lower()

    flags: list[str] = []
    for kw in _REJECT_KEYWORDS:
        if kw in haystack:
            flags.append(kw)
    if flags:
        return ComplianceResult(
            task_id="",  # filled in by caller
            verdict=ComplianceVerdict.REJECTED,
            risk_level=RiskLevel.RED,
            flags=flags,
            rationale=f"Triggered reject rules: {', '.join(flags)}",
        )

    for kw in _AMBER_KEYWORDS:
        if kw in haystack:
            flags.append(kw)
    if flags:
        return ComplianceResult(
            task_id="",
            verdict=ComplianceVerdict.REQUIRES_REVISION,
            risk_level=RiskLevel.AMBER,
            flags=flags,
            rationale=f"Triggered amber rules: {', '.join(flags)}",
        )

    return ComplianceResult(
        task_id="",
        verdict=ComplianceVerdict.APPROVED,
        risk_level=RiskLevel.GREEN,
        flags=[],
        rationale="No regulatory triggers matched (placeholder logic).",
    )


class ComplianceOfficer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.tracer = init_telemetry(service_name=settings.otel_service_name)
        self.redis = build_client()
        self.pg_pool = None
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
        logger.info(
            "Consuming stream=%s group=%s",
            self.settings.input_stream,
            self.settings.consumer_group,
        )
        async for msg in consume(
            self.redis,
            stream=self.settings.input_stream,
            group=self.settings.consumer_group,
            consumer=self.settings.consumer_name,
        ):
            if self._stop.is_set():
                break
            await self._handle(msg.message_id, msg.fields)

    async def _handle(self, redis_id: str, fields: dict[str, str]) -> None:
        with self.tracer.start_as_current_span(
            "compliance_officer.review", kind=SpanKind.CONSUMER
        ) as span:
            try:
                incoming = AgentMessage.from_stream_fields(fields)
                span.set_attribute("agent.task_id", incoming.task_id)

                await self._audit("in", incoming)

                assignment = incoming.data
                verdict = _evaluate(
                    assignment.get("description", ""),
                    assignment.get("inputs", {}),
                )
                verdict.task_id = incoming.task_id

                reply_payload = verdict.model_dump()
                reply_payload["status"] = MessageStatus.COMPLETED.value
                reply_payload["agent_id"] = self.settings.agent_id

                reply = AgentMessage(
                    from_agent=self.settings.agent_id,
                    to_agent=incoming.from_agent,
                    task_id=incoming.task_id,
                    message_type=MessageType.TASK_COMPLETE,
                    status=MessageStatus.COMPLETED,
                    data=reply_payload,
                    metadata={"in_reply_to": incoming.message_id, **incoming.metadata},
                )
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
                logger.exception("Compliance review failed (redis_id=%s)", redis_id)
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
            payload=message.data,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    officer = ComplianceOfficer(settings)
    await officer.start_pg()
    RedisInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()
    consumer_task = asyncio.create_task(officer.run(), name="compliance-consumer")
    app.state.officer = officer
    try:
        yield
    finally:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        await officer.close()


app = FastAPI(title="Compliance Officer", version="0.1.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, Any]:
    officer: ComplianceOfficer = app.state.officer
    try:
        await officer.redis.ping()
    except Exception as exc:
        return {"status": "not_ready", "error": str(exc)}
    return {"status": "ready"}
