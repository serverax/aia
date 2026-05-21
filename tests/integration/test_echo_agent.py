"""End-to-end test for the Echo Agent against the docker-compose dev stack.

Prereq: the agent + Postgres + Redis are running. Easiest path:

    docker compose -f infrastructure/docker-compose.dev.yml up -d

Then run:

    pytest tests/integration -m integration

This test:
  1. Publishes a unique AgentMessage on the input stream.
  2. Polls the output stream until the matching echo appears.
  3. Queries audit_log to confirm both `in` and `out` rows landed.
"""
from __future__ import annotations

import asyncio
import os
import uuid

import asyncpg
import pytest
import redis.asyncio as aioredis

from libs.communication import AgentMessage, MessageStatus, MessageType
from libs.communication.redis_client import publish

pytestmark = [pytest.mark.integration]

INPUT_STREAM = os.environ.get("ECHO_INPUT_STREAM", "agent:echo:tasks")
OUTPUT_STREAM = os.environ.get("ECHO_OUTPUT_STREAM", "agent:echo:results")
ECHO_AGENT_ID = os.environ.get("ECHO_AGENT_ID", "echo-agent-v1")


async def _wait_for_echo(
    client: aioredis.Redis,
    expected_task_id: str,
    timeout_seconds: float = 30.0,
) -> AgentMessage:
    """Tail OUTPUT_STREAM until we see a message matching our task_id."""
    deadline = asyncio.get_event_loop().time() + timeout_seconds
    last_id = "0"
    while asyncio.get_event_loop().time() < deadline:
        entries = await client.xread({OUTPUT_STREAM: last_id}, count=20, block=1000)
        for _, messages in entries or []:
            for msg_id, fields in messages:
                last_id = msg_id
                msg = AgentMessage.from_stream_fields(fields)
                if msg.task_id == expected_task_id:
                    return msg
    raise AssertionError(
        f"No echo for task_id={expected_task_id} within {timeout_seconds}s"
    )


@pytest.fixture
async def redis_client(require_dev_stack):
    client = aioredis.Redis(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        decode_responses=True,
    )
    yield client
    await client.close()


@pytest.fixture
async def pg_conn(require_dev_stack):
    conn = await asyncpg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "synthetic"),
        user=os.environ.get("POSTGRES_USER", "synthetic"),
        password=os.environ.get("POSTGRES_PASSWORD", "synthetic-dev"),
    )
    yield conn
    await conn.close()


async def test_echo_roundtrip_publishes_reply_and_audits(redis_client, pg_conn):
    task_id = f"itest-{uuid.uuid4()}"
    request = AgentMessage(
        from_agent="integration-test",
        to_agent=ECHO_AGENT_ID,
        task_id=task_id,
        message_type=MessageType.ECHO,
        status=MessageStatus.PENDING,
        data={"hello": "world", "task_id": task_id},
    )

    await publish(redis_client, INPUT_STREAM, request.to_stream_fields())

    reply = await _wait_for_echo(redis_client, task_id)

    assert reply.from_agent == ECHO_AGENT_ID
    assert reply.to_agent == "integration-test"
    assert reply.message_type is MessageType.ECHO
    assert reply.status is MessageStatus.COMPLETED
    assert reply.data["echoed"] == request.data

    # Audit log: one inbound, one outbound for this task.
    rows = await pg_conn.fetch(
        "SELECT direction, status FROM audit_log WHERE task_id = $1 ORDER BY id",
        task_id,
    )
    directions = [r["direction"] for r in rows]
    assert "in" in directions, f"missing inbound audit row, got {rows}"
    assert "out" in directions, f"missing outbound audit row, got {rows}"
