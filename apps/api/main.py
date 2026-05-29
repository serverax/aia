"""AIA / OrdinoxAI Hiring API — application entrypoint.

Run locally:

    uvicorn apps.api.main:app --reload --port 8080

Interactive docs at ``/docs``. The app starts even when Postgres is
unreachable (``/readyz`` reports 503) so it can serve docs and liveness in a
half-provisioned environment.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Security
from fastapi.middleware.cors import CORSMiddleware

from libs.auth import assert_auth_safe_for_production, get_current_active_user

from . import schemas
from .config import get_settings
from .db import PgDatabase
from .routers import applications, health
from .routers.crud import make_crud_router
from .scoring import build_scorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("aia.api")


def _build_crud_routers():
    """Instantiate the generic CRUD routers (everything but applications)."""
    return [
        make_crud_router(
            table="companies",
            prefix="/companies",
            tags=["companies"],
            create_model=schemas.CompanyCreate,
            update_model=schemas.CompanyUpdate,
            read_model=schemas.CompanyRead,
        ),
        make_crud_router(
            table="users",
            prefix="/users",
            tags=["users"],
            create_model=schemas.UserCreate,
            update_model=schemas.UserUpdate,
            read_model=schemas.UserRead,
        ),
        make_crud_router(
            table="jobs",
            prefix="/jobs",
            tags=["jobs"],
            create_model=schemas.JobCreate,
            update_model=schemas.JobUpdate,
            read_model=schemas.JobRead,
        ),
        make_crud_router(
            table="candidates",
            prefix="/candidates",
            tags=["candidates"],
            create_model=schemas.CandidateCreate,
            update_model=schemas.CandidateUpdate,
            read_model=schemas.CandidateRead,
        ),
        make_crud_router(
            table="interviews",
            prefix="/interviews",
            tags=["interviews"],
            create_model=schemas.InterviewCreate,
            update_model=schemas.InterviewUpdate,
            read_model=schemas.InterviewRead,
        ),
        make_crud_router(
            table="waitlist_users",
            prefix="/waitlist",
            tags=["waitlist"],
            create_model=schemas.WaitlistCreate,
            update_model=schemas.WaitlistUpdate,
            read_model=schemas.WaitlistRead,
        ),
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail loudly at startup if a production env is still on dev-only auth
    # (in-memory fake_users_db / dev-default JWT secret). No-op in dev. Mirrors
    # services/orchestrator_agent/main.py:OrchestratorService.start().
    assert_auth_safe_for_production()
    settings = get_settings()
    app.state.scorer = build_scorer(
        api_key=settings.anthropic_api_key, model=settings.anthropic_model
    )
    app.state.db = None
    try:
        app.state.db = await PgDatabase.connect(
            settings.dsn(),
            schema=settings.db_schema,
            min_size=settings.db_pool_min,
            max_size=settings.db_pool_max,
        )
        logger.info("connected to Postgres schema %s", settings.db_schema)
    except Exception:  # noqa: BLE001 - degrade gracefully; /readyz reports it
        logger.exception("could not connect to Postgres at startup; running degraded")

    try:
        yield
    finally:
        if app.state.db is not None:
            await app.state.db.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AIA / OrdinoxAI Hiring API",
        version="0.1.0",
        description="CRUD + AI scoring over the ordinoxai schema.",
        lifespan=lifespan,
    )

    origins = settings.cors_origin_list()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Hiring data (companies/users/jobs/candidates/applications/waitlist) handles
    # PII — every CRUD + scoring route requires an authenticated user (scope
    # "items"). Health probes and the metadata root stay public.
    require_user = Security(get_current_active_user, scopes=["items"])

    app.include_router(health.router)
    for router in _build_crud_routers():
        app.include_router(router, dependencies=[require_user])
    app.include_router(applications.router, dependencies=[require_user])

    @app.get("/", tags=["meta"], summary="Service metadata")
    async def root() -> dict[str, str]:
        return {
            "service": settings.service_name,
            "environment": settings.environment,
            "schema": settings.db_schema,
            "docs": "/docs",
        }

    return app


app = create_app()
