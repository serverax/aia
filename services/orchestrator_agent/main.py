"""Orchestrator service entry point.

FastAPI for HTTP entry (POST /requests) plus a background consumer on
`orchestrator:requests` so other services can also submit requests via
Redis. Both paths feed the same LangGraph invocation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Security, status
from fastapi.security import OAuth2PasswordRequestForm
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from libs.auth import (
    Token,
    User,
    assert_auth_safe_for_production,
    authenticate_user,
    create_access_token,
    get_current_active_user,
)
from libs.communication.postgres_client import build_pool
from libs.communication.redis_client import ack, build_client, consume
from libs.communication.telemetry import init_telemetry
from libs.llm import LLMClient, build_default_client
from services.orchestrator_agent.compliance_gate import ComplianceGate
from services.orchestrator_agent.graph import build_graph
from services.orchestrator_agent.state import OrchestratorState


def _build_tool_verifier():
    """Construct the SignatureVerifier the registry uses.

    Production: read PEM from `/etc/aia-cosign/cosign.pub` (mounted from the
    cosign-system/aia-cosign-pubkey ConfigMap by Sprint 6 deploy).
    Dev: if that file is missing, fall back to AllowAllVerifier with a loud
    warning so test runs without signed artifacts still work.
    """
    from pathlib import Path

    from services.tool_sandbox import CosignVerifier
    from services.tool_sandbox.verifier import AllowAllVerifier

    pubkey_path = Path(os.environ.get("AIA_COSIGN_PUBKEY", "/etc/aia-cosign/cosign.pub"))
    if pubkey_path.is_file():
        return CosignVerifier(pubkey_path.read_bytes())
    logger.warning(
        "Cosign public key not found at %s; using AllowAllVerifier. "
        "Production deploys MUST mount the cosign-system/aia-cosign-pubkey ConfigMap.",
        pubkey_path,
    )
    return AllowAllVerifier()


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_id: str = "orchestrator-v1"
    request_stream: str = "orchestrator:requests"
    reply_stream: str = "orchestrator:replies"
    request_consumer_group: str = "orchestrators"
    request_consumer_name: str = "orchestrator-1"
    max_concurrent_dispatches: int = 20
    monitor_timeout_seconds: float = 60.0
    audit_enabled: bool = True
    otel_service_name: str = "orchestrator"

    # Sprint 6: optional WASM tool registry. If TOOLS_ROOT is set and points
    # to a directory containing tool.yaml entries, a ToolRegistry is built
    # at startup and exposed at app.state.tool_registry for nodes that need
    # tool-use chats. Unset = no tools = current behavior.
    tools_root: str | None = None

    # Sprint 7: kill-switch admission gate. If COMPLIANCE_SERVICE_URL is set,
    # each request is checked against the Compliance Service before the graph
    # runs; a denied project/global kill-switch short-circuits with a
    # "rejected_by_compliance" phase. Unset = gating disabled (dev default).
    compliance_service_url: str = ""


settings = Settings()


class RequestPayload(BaseModel):
    user_request: str
    project_id: str | None = None


class OrchestratorService:
    """Holds shared clients + graph for the service lifetime."""

    def __init__(
        self,
        settings: Settings,
        llm: LLMClient | None = None,
        compliance_gate: ComplianceGate | None = None,
    ) -> None:
        self.settings = settings
        self.tracer = init_telemetry(service_name=settings.otel_service_name)
        self.redis = build_client()
        self.pg_pool = None
        self.llm = llm or build_default_client()
        self.graph = None  # built after pg pool is ready
        self.tool_registry = None  # populated in start() if tools_root is set
        # Injectable for tests; otherwise built in start() from settings.
        self.compliance_gate = compliance_gate
        self._stop = asyncio.Event()

    async def start(self) -> None:
        # Fail loudly at startup if a production env is still on dev-only auth
        # (in-memory users / dev-default JWT secret). No-op in dev.
        assert_auth_safe_for_production()
        if self.settings.audit_enabled:
            self.pg_pool = await build_pool()
        if self.compliance_gate is None and self.settings.compliance_service_url:
            self.compliance_gate = ComplianceGate(base_url=self.settings.compliance_service_url)
            logger.info(
                "Compliance admission gate enabled -> %s", self.settings.compliance_service_url
            )
        if self.settings.tools_root:
            # Imported here so the orchestrator can still run without the
            # tool_sandbox optional deps installed (e.g. minimal dev images).
            from pathlib import Path

            from services.tool_sandbox import ToolRegistry, WasmExecutor
            from services.tool_sandbox.audit_adapter import PostgresToolAuditSink

            verifier = _build_tool_verifier()
            audit_sink = (
                PostgresToolAuditSink(self.pg_pool, self.settings.agent_id)
                if self.pg_pool
                else None
            )
            self.tool_registry = ToolRegistry(
                tools_root=Path(self.settings.tools_root),
                verifier=verifier,
                executor=WasmExecutor(),
                audit_sink=audit_sink,
            )
            logger.info(
                "ToolRegistry loaded %d tools from %s",
                len(self.tool_registry.names()),
                self.settings.tools_root,
            )
        self.graph = build_graph(
            llm=self.llm,
            redis_client=self.redis,
            pg_pool=self.pg_pool,
            max_concurrent_dispatches=self.settings.max_concurrent_dispatches,
            monitor_timeout_seconds=self.settings.monitor_timeout_seconds,
        )

    async def close(self) -> None:
        self._stop.set()
        await self.redis.close()
        if self.pg_pool:
            await self.pg_pool.close()

    async def handle_request(self, payload: RequestPayload) -> OrchestratorState:
        """Synchronously run the graph for one request.

        If a compliance gate is configured, the request is checked against the
        kill-switch first; a denial short-circuits before the graph runs.
        """
        project_id = payload.project_id or f"proj-{uuid.uuid4()}"

        if self.compliance_gate is not None:
            decision = await self.compliance_gate.check(
                agent_id=self.settings.agent_id, project_id=project_id
            )
            if not decision.allowed:
                logger.warning(
                    "request for project %s rejected by compliance gate: %s",
                    project_id,
                    decision.reason,
                )
                return {
                    "user_request": payload.user_request,
                    "project_id": project_id,
                    "current_phase": "rejected_by_compliance",
                    "dispatched_task_ids": [],
                    "results": {},
                    "compliance": {
                        "allowed": False,
                        "reason": decision.reason,
                        "source": decision.source,
                        "policy_version": decision.policy_version,
                    },
                }

        initial: OrchestratorState = {
            "user_request": payload.user_request,
            "project_id": project_id,
            "current_phase": "parsing",
            "dispatched_task_ids": [],
            "results": {},
        }
        # ainvoke returns the terminal state.
        return await self.graph.ainvoke(initial)

    async def consume_requests(self) -> None:
        """Background loop reading the requests stream."""
        logger.info(
            "Consuming stream=%s group=%s consumer=%s",
            self.settings.request_stream,
            self.settings.request_consumer_group,
            self.settings.request_consumer_name,
        )
        async for msg in consume(
            self.redis,
            stream=self.settings.request_stream,
            group=self.settings.request_consumer_group,
            consumer=self.settings.request_consumer_name,
        ):
            if self._stop.is_set():
                break
            try:
                raw = msg.fields.get("request") or json.dumps(msg.fields)
                payload = (
                    RequestPayload.model_validate_json(raw)
                    if raw.startswith("{")
                    else RequestPayload(user_request=raw)
                )
                await self.handle_request(payload)
                await ack(
                    self.redis,
                    stream=self.settings.request_stream,
                    group=self.settings.request_consumer_group,
                    message_id=msg.message_id,
                )
            except Exception:
                logger.exception("Failed handling request %s", msg.message_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = OrchestratorService(settings)
    await service.start()
    RedisInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()
    consumer_task = asyncio.create_task(service.consume_requests(), name="orchestrator-requests")
    app.state.service = service
    try:
        yield
    finally:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        await service.close()


app = FastAPI(title="Orchestrator", version="0.1.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, Any]:
    service: OrchestratorService = app.state.service
    try:
        await service.redis.ping()
    except Exception as exc:
        return {"status": "not_ready", "error": str(exc)}
    return {"status": "ready"}


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> dict[str, str]:
    from fastapi import HTTPException

    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username, "scopes": user.scopes})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/requests")
async def submit_request(
    payload: RequestPayload,
    current_user: User = Security(get_current_active_user, scopes=["items"]),
) -> dict[str, Any]:
    """HTTP entry point — handy for curl / dashboard."""
    service: OrchestratorService = app.state.service
    final_state = await service.handle_request(payload)
    return {
        "project_id": final_state["project_id"],
        "phase": final_state.get("current_phase"),
        "task_count": len(final_state.get("tasks", [])),
        "results": final_state.get("results", {}),
        "conflicts": final_state.get("conflicts", []),
        "escalated": final_state.get("escalated", False),
    }
