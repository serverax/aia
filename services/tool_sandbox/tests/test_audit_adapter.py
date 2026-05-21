"""Unit tests for PostgresToolAuditSink with a mocked asyncpg pool."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.tool_sandbox.audit_adapter import PostgresToolAuditSink, _digest

pytestmark = [pytest.mark.unit]


def test_digest_is_stable_and_64_hex_chars():
    a = _digest({"x": 1, "y": [1, 2, 3]})
    b = _digest({"y": [1, 2, 3], "x": 1})  # different key order, same content
    assert a == b
    assert len(a) == 64
    assert all(c in "0123456789abcdef" for c in a)


def test_digest_for_empty_payload_is_constant():
    assert _digest(None) == "0" * 64
    assert _digest({}) == "0" * 64


class _FakeConn:
    def __init__(self, captured: list):
        self._captured = captured

    async def execute(self, sql: str, *args):
        self._captured.append((sql, args))


class _FakePool:
    """Mimic asyncpg.Pool.acquire() async context manager."""

    def __init__(self):
        self.captured: list = []

    def acquire(self):
        pool = self

        class _Cm:
            async def __aenter__(self):
                return _FakeConn(pool.captured)

            async def __aexit__(self, *_):
                return False
        return _Cm()


async def test_record_writes_one_audit_row():
    pool = _FakePool()
    sink = PostgresToolAuditSink(pool, default_agent_id="analyst-v1")
    await sink.record(
        agent_id="analyst-v1",
        tool_name="parse_dates_v3",
        tool_version="0.1.0",
        status="ok",
        input_payload={"text": "hi"},
        output_payload={"dates": []},
        error=None,
    )
    assert len(pool.captured) == 1
    sql, args = pool.captured[0]
    assert "INSERT INTO audit_log" in sql
    # args: timestamp, agent_id, message_id, task_id, direction, message_type, status, payload
    assert args[1] == "analyst-v1"
    assert args[3] == "parse_dates_v3:0.1.0"   # task_id
    assert args[4] == "tool"                    # direction
    assert args[5] == "tool_call"               # message_type
    assert args[6] == "ok"                      # status
    # payload is JSON string with both digests + no error
    import json
    payload = json.loads(args[7])
    assert payload["tool_name"] == "parse_dates_v3"
    assert payload["error"] is None
    assert len(payload["input_sha256"]) == 64
    assert len(payload["output_sha256"]) == 64


async def test_record_swallows_db_errors_without_raising():
    """The tool call already happened — an audit failure must not poison it."""

    class _BoomPool:
        def acquire(self):
            class _Cm:
                async def __aenter__(self):
                    raise RuntimeError("db is down")
                async def __aexit__(self, *_):
                    return False
            return _Cm()

    sink = PostgresToolAuditSink(_BoomPool(), default_agent_id="x")
    # Must not raise.
    await sink.record(
        agent_id="x",
        tool_name="t",
        tool_version="1",
        status="error",
        input_payload={},
        output_payload={},
        error="anything",
    )


async def test_record_falls_back_to_default_agent_id_when_missing():
    pool = _FakePool()
    sink = PostgresToolAuditSink(pool, default_agent_id="fallback")
    await sink.record(
        agent_id="",          # caller forgot to pass it
        tool_name="t",
        tool_version="1",
        status="ok",
        input_payload={},
        output_payload={},
        error=None,
    )
    assert pool.captured[0][1][1] == "fallback"
