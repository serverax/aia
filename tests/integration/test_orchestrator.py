"""End-to-end test of the Orchestrator graph against a real Redis + a real
Compliance Officer running in docker-compose.

The LLM is stubbed (no API key needed) so the test is deterministic: the
stub returns a known intent and a task graph containing a task description
that will trigger the Compliance Officer's REJECT rule. We then verify:

  1. The router published a TASK_ASSIGNMENT to `agent:compliance_officer:tasks`.
  2. The Compliance Officer replied on `orchestrator:replies` with verdict=REJECTED.
  3. The orchestrator detected the conflict and published an escalation.
  4. audit_log contains the full chain.

Prereq:
    docker compose -f infrastructure/docker-compose.dev.yml up -d \
        postgres redis jaeger compliance-agent
"""
from __future__ import annotations

import asyncio
import os
import uuid

import asyncpg
import pytest
import redis.asyncio as aioredis

from libs.communication import AgentMessage
from libs.llm import StubLLMClient
from services.orchestrator_agent.graph import build_graph

pytestmark = [pytest.mark.integration]


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
async def pg_pool(require_dev_stack):
    pool = await asyncpg.create_pool(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "synthetic"),
        user=os.environ.get("POSTGRES_USER", "synthetic"),
        password=os.environ.get("POSTGRES_PASSWORD", "synthetic-dev"),
        min_size=1,
        max_size=2,
    )
    yield pool
    await pool.close()


async def test_orchestrator_dispatches_routes_and_escalates_on_veto(
    redis_client, pg_pool
):
    project_id = f"proj-{uuid.uuid4()}"
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    # Canned LLM responses: parse intent, then return a single compliance task
    # whose description triggers the REJECT keyword.
    stub = StubLLMClient(
        [
            {
                "objective": "Audit a clause for GDPR compliance",
                "domain": "employment_law",
                "scope": "UK",
                "constraints": [],
                "ambiguities": [],
                "requires_clarification": False,
                "clarification_questions": [],
            },
            {
                "tasks": [
                    {
                        "id": task_id,
                        "name": "Compliance check",
                        "description": "Verify there is no violation of GDPR Article 6",
                        "assigned_to": "compliance_officer",
                        "inputs": {},
                        "expected_outputs": ["verdict"],
                        "depends_on": [],
                        "priority": "critical",
                        "deadline": None,
                    }
                ]
            },
        ]
    )

    graph = build_graph(
        llm=stub,
        redis_client=redis_client,
        pg_pool=pg_pool,
        max_concurrent_dispatches=4,
        monitor_timeout_seconds=15.0,
    )

    final_state = await graph.ainvoke(
        {
            "user_request": "Audit our settlement clause",
            "project_id": project_id,
            "current_phase": "parsing",
            "dispatched_task_ids": [],
            "results": {},
        }
    )

    # Graph terminated.
    assert final_state.get("current_phase") == "done"

    # Compliance Officer replied within the monitor window.
    assert task_id in final_state["results"], (
        f"No reply for {task_id}; got {final_state.get('results')} "
        f"(timed_out={final_state.get('timed_out_task_ids')})"
    )
    reply = final_state["results"][task_id]
    assert reply.get("verdict") == "rejected", reply
    assert reply.get("risk_level") == "red", reply

    # Orchestrator escalated.
    assert final_state.get("escalated") is True
    assert len(final_state.get("conflicts", [])) >= 1

    # Escalation envelope published on the dedicated stream.
    escalations = await redis_client.xrange("orchestrator:escalations")
    escalation_for_us = [
        AgentMessage.from_stream_fields(fields)
        for _, fields in escalations
        if AgentMessage.from_stream_fields(fields).metadata.get("project_id") == project_id
    ]
    assert escalation_for_us, "no escalation envelope for this project"

    # Audit log has the orchestrator's escalation row AND the compliance
    # officer's in/out rows for this task.
    rows = await pg_pool.fetch(
        "SELECT agent_id, direction, message_type FROM audit_log WHERE task_id = $1",
        task_id,
    )
    agent_ids = {r["agent_id"] for r in rows}
    assert "compliance-officer-v1" in agent_ids, rows
    assert "orchestrator-v1" in agent_ids, rows


async def test_orchestrator_completes_cleanly_when_no_conflict(redis_client, pg_pool):
    """Same flow but with a benign task — should NOT escalate."""
    project_id = f"proj-{uuid.uuid4()}"
    task_id = f"task-{uuid.uuid4().hex[:8]}"

    stub = StubLLMClient(
        [
            {
                "objective": "Draft a vanilla NDA",
                "domain": "contract_law",
                "scope": "UK",
                "constraints": [],
                "ambiguities": [],
                "requires_clarification": False,
                "clarification_questions": [],
            },
            {
                "tasks": [
                    {
                        "id": task_id,
                        "name": "Compliance check",
                        "description": "Standard mutual NDA wording review",
                        "assigned_to": "compliance_officer",
                        "inputs": {},
                        "expected_outputs": ["verdict"],
                        "depends_on": [],
                        "priority": "normal",
                        "deadline": None,
                    }
                ]
            },
        ]
    )

    graph = build_graph(
        llm=stub,
        redis_client=redis_client,
        pg_pool=pg_pool,
        monitor_timeout_seconds=15.0,
    )
    final_state = await graph.ainvoke(
        {
            "user_request": "Draft NDA",
            "project_id": project_id,
            "current_phase": "parsing",
            "dispatched_task_ids": [],
            "results": {},
        }
    )

    assert final_state.get("escalated") is False
    assert final_state.get("conflicts", []) == []
    assert final_state["results"][task_id]["verdict"] == "approved"
