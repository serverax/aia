"""Async Postgres helpers focused on the audit log.

The audit log records every message an agent processes. Tables are created
by `infrastructure/k3s/postgres-init.sql` and reused here. This module
intentionally exposes a small surface: a pool factory and an `audit()`
writer. Richer queries should live in service-specific modules.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


def _dsn(
    host: str | None = None,
    port: int | None = None,
    database: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> str:
    return "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=user or os.environ.get("POSTGRES_USER", "synthetic"),
        password=password or os.environ.get("POSTGRES_PASSWORD", "synthetic-dev"),
        host=host or os.environ.get("POSTGRES_HOST", "localhost"),
        port=port or int(os.environ.get("POSTGRES_PORT", "5432")),
        db=database or os.environ.get("POSTGRES_DB", "synthetic"),
    )


async def build_pool(
    min_size: int = 1,
    max_size: int = 10,
    **dsn_overrides: Any,
) -> asyncpg.Pool:
    """Build a connection pool. Service should hold one for its lifetime."""
    return await asyncpg.create_pool(
        dsn=_dsn(**dsn_overrides),
        min_size=min_size,
        max_size=max_size,
    )


async def audit(
    pool: asyncpg.Pool,
    *,
    agent_id: str,
    message_id: str,
    task_id: str,
    direction: str,
    message_type: str,
    status: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append a row to audit_log.

    `direction` is "in" or "out" describing whether the agent received or
    emitted the message. `payload` is stored as jsonb.
    """
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO audit_log
                (timestamp, agent_id, message_id, task_id, direction,
                 message_type, status, payload)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
            """,
            datetime.now(timezone.utc),
            agent_id,
            message_id,
            task_id,
            direction,
            message_type,
            status,
            json.dumps(payload or {}),
        )
