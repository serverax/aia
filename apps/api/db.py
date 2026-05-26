"""Data-access layer for the Hiring API.

Two interchangeable implementations of the same small surface:

* :class:`PgDatabase` — asyncpg-backed, talks to the live ``ordinoxai`` schema.
* :class:`FakeDatabase` — in-memory, used by the test suite so QA runs with
  neither a Postgres instance nor an Anthropic API key.

All dynamic SQL interpolates identifiers only from :mod:`apps.api.tables`;
every value is a bound parameter. See that module for why that is safe.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

import asyncpg

from .tables import TABLES, TableSpec

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _spec(table: str) -> TableSpec:
    try:
        return TABLES[table]
    except KeyError as exc:  # pragma: no cover - guards programmer error
        raise ValueError(f"unknown table {table!r}") from exc


def _enc(value: Any) -> Any:
    """Coerce Python types asyncpg can't bind directly.

    Pydantic hands us ``float`` for ``numeric`` columns; asyncpg's numeric
    codec wants ``Decimal``. jsonb/uuid/datetime are handled by codecs set on
    each connection (see :func:`_init_connection`).
    """
    if isinstance(value, float):
        return Decimal(str(value))
    return value


def clamp_limit(limit: int) -> int:
    return max(1, min(limit, _MAX_LIMIT))


class Database(Protocol):
    async def insert(self, table: str, data: dict[str, Any]) -> dict[str, Any]: ...

    async def get(self, table: str, row_id: UUID) -> dict[str, Any] | None: ...

    async def list(
        self,
        table: str,
        *,
        filters: dict[str, str] | None = None,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str = "desc",
    ) -> list[dict[str, Any]]: ...

    async def update(
        self, table: str, row_id: UUID, data: dict[str, Any]
    ) -> dict[str, Any] | None: ...

    async def delete(self, table: str, row_id: UUID) -> bool: ...

    async def audit(
        self,
        *,
        entity_type: str,
        action: str,
        entity_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        old_data: dict[str, Any] | None = None,
        new_data: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None: ...

    async def ping(self) -> None: ...


# --------------------------------------------------------------------------- #
# Postgres implementation
# --------------------------------------------------------------------------- #


async def _init_connection(conn: asyncpg.Connection, schema: str) -> None:
    await conn.execute(f'SET search_path TO "{schema}", public')
    for typ in ("jsonb", "json"):
        await conn.set_type_codec(
            typ,
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )


class PgDatabase:
    """asyncpg-backed implementation. Hold one instance for the app lifetime."""

    def __init__(self, pool: asyncpg.Pool, schema: str) -> None:
        self._pool = pool
        self._schema = schema

    @classmethod
    async def connect(cls, dsn: str, *, schema: str, min_size: int, max_size: int) -> "PgDatabase":
        async def init(conn: asyncpg.Connection) -> None:
            await _init_connection(conn, schema)

        pool = await asyncpg.create_pool(dsn=dsn, min_size=min_size, max_size=max_size, init=init)
        return cls(pool, schema)

    async def close(self) -> None:
        await self._pool.close()

    def _tbl(self, table: str) -> str:
        return f'"{self._schema}"."{table}"'

    async def insert(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        spec = _spec(table)
        cols = [c for c in spec.writable if c in data]
        if not cols:
            sql = f"INSERT INTO {self._tbl(table)} DEFAULT VALUES RETURNING *"
            args: list[Any] = []
        else:
            collist = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(f"${i}" for i in range(1, len(cols) + 1))
            sql = (
                f"INSERT INTO {self._tbl(table)} ({collist}) "
                f"VALUES ({placeholders}) RETURNING *"
            )
            args = [_enc(data[c]) for c in cols]
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *args)
        return dict(row)

    async def get(self, table: str, row_id: UUID) -> dict[str, Any] | None:
        _spec(table)
        sql = f'SELECT * FROM {self._tbl(table)} WHERE "id" = $1'
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, row_id)
        return dict(row) if row else None

    async def list(
        self,
        table: str,
        *,
        filters: dict[str, str] | None = None,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str = "desc",
    ) -> list[dict[str, Any]]:
        spec = _spec(table)
        filters = filters or {}
        conditions: list[str] = []
        args: list[Any] = []
        for col, val in filters.items():
            if col not in spec.filterable:
                continue
            args.append(val)
            # Compare as text so a string query param matches uuid/enum columns.
            conditions.append(f'"{col}"::text = ${len(args)}')

        order_col = order_by if order_by in spec.orderable() else spec.default_order
        direction = "ASC" if order_dir.lower() == "asc" else "DESC"

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        args.append(clamp_limit(limit))
        limit_ph = f"${len(args)}"
        args.append(max(0, offset))
        offset_ph = f"${len(args)}"
        sql = (
            f"SELECT * FROM {self._tbl(table)}{where} "
            f'ORDER BY "{order_col}" {direction} '
            f"LIMIT {limit_ph} OFFSET {offset_ph}"
        )
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *args)
        return [dict(r) for r in rows]

    async def update(self, table: str, row_id: UUID, data: dict[str, Any]) -> dict[str, Any] | None:
        spec = _spec(table)
        cols = [c for c in spec.writable if c in data]
        if not cols:
            return await self.get(table, row_id)
        set_clause = ", ".join(f'"{c}" = ${i}' for i, c in enumerate(cols, start=1))
        sql = (
            f"UPDATE {self._tbl(table)} SET {set_clause} "
            f'WHERE "id" = ${len(cols) + 1} RETURNING *'
        )
        args = [_enc(data[c]) for c in cols] + [row_id]
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *args)
        return dict(row) if row else None

    async def delete(self, table: str, row_id: UUID) -> bool:
        _spec(table)
        sql = f'DELETE FROM {self._tbl(table)} WHERE "id" = $1 RETURNING "id"'
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, row_id)
        return row is not None

    async def audit(
        self,
        *,
        entity_type: str,
        action: str,
        entity_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        old_data: dict[str, Any] | None = None,
        new_data: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        sql = (
            f"INSERT INTO {self._tbl('audit_logs')} "
            "(actor_user_id, entity_type, entity_id, action, old_data, new_data, "
            " ip_address, user_agent) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)"
        )
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    sql,
                    actor_user_id,
                    entity_type,
                    entity_id,
                    action,
                    old_data,
                    new_data,
                    ip_address,
                    user_agent,
                )
        except Exception:  # noqa: BLE001 - audit must never break the request
            logger.exception("audit write failed for %s %s", entity_type, action)

    async def ping(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("SELECT 1")


# --------------------------------------------------------------------------- #
# In-memory implementation (tests)
# --------------------------------------------------------------------------- #


class FakeDatabase:
    """Dict-backed stand-in with the same surface as :class:`PgDatabase`."""

    def __init__(self) -> None:
        self._data: dict[str, dict[UUID, dict[str, Any]]] = {t: {} for t in TABLES}
        self.audits: list[dict[str, Any]] = []

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    async def insert(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        spec = _spec(table)
        row_id = uuid4()
        now = self._now()
        row: dict[str, Any] = {"id": row_id, "created_at": now, "updated_at": now}
        if table == "applications":
            row.setdefault("submitted_at", now)
        for col in spec.writable:
            if col in data:
                row[col] = data[col]
        self._data[table][row_id] = row
        return dict(row)

    async def get(self, table: str, row_id: UUID) -> dict[str, Any] | None:
        _spec(table)
        row = self._data[table].get(row_id)
        return dict(row) if row else None

    async def list(
        self,
        table: str,
        *,
        filters: dict[str, str] | None = None,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str = "desc",
    ) -> list[dict[str, Any]]:
        spec = _spec(table)
        filters = filters or {}
        rows = list(self._data[table].values())
        for col, val in filters.items():
            if col not in spec.filterable:
                continue
            rows = [r for r in rows if str(r.get(col)) == str(val)]
        order_col = order_by if order_by in spec.orderable() else spec.default_order
        rows.sort(
            key=lambda r: (r.get(order_col) is not None, r.get(order_col)),
            reverse=order_dir.lower() != "asc",
        )
        sliced = rows[max(0, offset) : max(0, offset) + clamp_limit(limit)]
        return [dict(r) for r in sliced]

    async def update(self, table: str, row_id: UUID, data: dict[str, Any]) -> dict[str, Any] | None:
        spec = _spec(table)
        row = self._data[table].get(row_id)
        if row is None:
            return None
        for col in spec.writable:
            if col in data:
                row[col] = data[col]
        row["updated_at"] = self._now()
        return dict(row)

    async def delete(self, table: str, row_id: UUID) -> bool:
        _spec(table)
        return self._data[table].pop(row_id, None) is not None

    async def audit(self, **kwargs: Any) -> None:
        self.audits.append(kwargs)

    async def ping(self) -> None:
        return None
