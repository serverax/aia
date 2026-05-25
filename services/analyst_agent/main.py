"""Domain Analyst Agent — Sprint 6 skeleton demonstrating tool use.

Receives task assignments on `agent:domain_analyst:tasks`, runs a Claude
agent_loop with the registered WASM tools enabled, and publishes the
final assistant text back on `orchestrator:replies`.

Sprint 3 (Gemini) will replace the Claude tool-use loop with a richer
RAG pipeline against Milvus (`milvus_manager.py` already exists in this
folder as their Sprint 3 stub). Sprint 6 ships the agent-loop plumbing
so when Sprint 3 starts there's a working tool-use foundation to extend.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

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
from libs.llm import LLMClient, agent_loop, build_default_client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_id: str = "analyst-v1"
    input_stream: str = "agent:domain_analyst:tasks"
    reply_stream: str = "orchestrator:replies"
    consumer_group: str = "domain-analysts"
    consumer_name: str = "analyst-1"
    audit_enabled: bool = True
    otel_service_name: str = "analyst"

    # Tool registry; same env var as Orchestrator. If unset, agent_loop is
    # called with an empty tool list (LLM-only Q&A).
    tools_root: str | None = None
    max_loop_iterations: int = 8

    system_prompt: str = (
        "You are a domain analyst at a UK legal-tech platform. "
        "Use the provided tools when they help extract structured facts "
        "from text. Cite the tool name in your final answer."
    )


settings = Settings()


def _build_tool_verifier():
    from services.tool_sandbox import CosignVerifier
    from services.tool_sandbox.verifier import AllowAllVerifier

    pubkey_path = Path(os.environ.get("AIA_COSIGN_PUBKEY", "/etc/aia-cosign/cosign.pub"))
    if pubkey_path.is_file():
        return CosignVerifier(pubkey_path.read_bytes())
    logger.warning("cosign pubkey not found at %s; using AllowAllVerifier (dev only).", pubkey_path)
    return AllowAllVerifier()


class AnalystAgent:
    def __init__(self, settings: Settings, llm: LLMClient | None = None) -> None:
        self.settings = settings
        self.tracer = init_telemetry(service_name=settings.otel_service_name)
        self.redis = build_client()
        self.pg_pool = None
        self.llm = llm or build_default_client()
        self.tool_registry = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self.settings.audit_enabled:
            self.pg_pool = await build_pool()
        if self.settings.tools_root:
            from services.tool_sandbox import ToolRegistry, WasmExecutor
            from services.tool_sandbox.audit_adapter import PostgresToolAuditSink

            audit_sink = (
                PostgresToolAuditSink(self.pg_pool, self.settings.agent_id)
                if self.pg_pool
                else None
            )
            self.tool_registry = ToolRegistry(
                tools_root=Path(self.settings.tools_root),
                verifier=_build_tool_verifier(),
                executor=WasmExecutor(),
                audit_sink=audit_sink,
            )
            logger.info(
                "ToolRegistry loaded %d tools from %s: %s",
                len(self.tool_registry.names()),
                self.settings.tools_root,
                self.tool_registry.names(),
            )

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
        ):
            if self._stop.is_set():
                break
            await self._handle(msg.message_id, msg.fields)

    async def _handle(self, redis_id: str, fields: dict[str, str]) -> None:
        with self.tracer.start_as_current_span("analyst.handle", kind=SpanKind.CONSUMER) as span:
            try:
                incoming = AgentMessage.from_stream_fields(fields)
                span.set_attribute("agent.task_id", incoming.task_id)
                await self._audit("in", incoming)

                assignment = incoming.data
                user_prompt = assignment.get("description") or json.dumps(assignment)

                tools = self._tool_descriptors_for_agent()
                tool_exec = self.tool_registry.execute if self.tool_registry else _no_tools_executor

                response = await agent_loop(
                    llm=self.llm,
                    agent_id=self.settings.agent_id,
                    initial_messages=[{"role": "user", "content": user_prompt}],
                    tool_descriptors=tools,
                    tool_executor=tool_exec,
                    system=self.settings.system_prompt,
                    max_iterations=self.settings.max_loop_iterations,
                )

                reply = AgentMessage(
                    from_agent=self.settings.agent_id,
                    to_agent=incoming.from_agent,
                    task_id=incoming.task_id,
                    message_type=MessageType.TASK_COMPLETE,
                    status=MessageStatus.COMPLETED,
                    data={
                        "agent_id": self.settings.agent_id,
                        "status": MessageStatus.COMPLETED.value,
                        "output": response.text,
                        "tool_use_iterations": (
                            len(self.llm.tool_calls) if hasattr(self.llm, "tool_calls") else None
                        ),
                    },
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
                logger.exception("analyst handling failed (redis_id=%s)", redis_id)
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))

    def _tool_descriptors_for_agent(self) -> list:
        if not self.tool_registry:
            return []
        return [
            self.tool_registry.get(name)
            for name in self.tool_registry.names()
            if self.tool_registry.is_allowed(self.settings.agent_id, name)
        ]

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


async def _no_tools_executor(agent_id: str, tool_name: str, input_payload: dict[str, Any]):
    raise RuntimeError(
        f"Agent {agent_id!r} attempted to use tool {tool_name!r} "
        f"but no ToolRegistry is configured (set TOOLS_ROOT env var)."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    agent = AnalystAgent(settings)
    await agent.start()
    RedisInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()
    consumer_task = asyncio.create_task(agent.run(), name="analyst-consumer")
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


app = FastAPI(title="Domain Analyst", version="0.1.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, Any]:
    agent: AnalystAgent = app.state.agent
    try:
        await agent.redis.ping()
    except Exception as exc:
        return {"status": "not_ready", "error": str(exc)}
    return {
        "status": "ready",
        "tools_loaded": agent.tool_registry.names() if agent.tool_registry else [],
    }
