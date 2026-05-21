"""Unit tests for the router using fakeredis (no real Redis required)."""
from __future__ import annotations

import json

import fakeredis.aioredis
import pytest

from libs.communication import AgentMessage
from services.orchestrator_agent.router import _ready, make_router

pytestmark = [pytest.mark.unit]


def test_ready_when_no_deps():
    assert _ready({"id": "t", "depends_on": []}, set())


def test_not_ready_when_deps_unmet():
    assert not _ready({"id": "t", "depends_on": ["a"]}, set())


def test_ready_when_deps_met():
    assert _ready({"id": "t", "depends_on": ["a", "b"]}, {"a", "b"})


async def test_router_dispatches_to_correct_stream():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    router = make_router(redis, max_concurrent=2)

    state = {
        "project_id": "proj-1",
        "tasks": [
            {"id": "t1", "name": "research", "assigned_to": "domain_analyst", "depends_on": []},
            {"id": "t2", "name": "verify", "assigned_to": "compliance_officer", "depends_on": []},
        ],
        "dispatched_task_ids": [],
    }
    updated = await router(state)

    assert set(updated["dispatched_task_ids"]) == {"t1", "t2"}
    assert updated["current_phase"] == "monitoring"

    analyst_entries = await redis.xrange("agent:domain_analyst:tasks")
    compliance_entries = await redis.xrange("agent:compliance_officer:tasks")
    assert len(analyst_entries) == 1
    assert len(compliance_entries) == 1

    # Verify envelope round-trips cleanly through AgentMessage.
    _, fields = analyst_entries[0]
    envelope = AgentMessage.from_stream_fields(fields)
    assert envelope.task_id == "t1"
    assert envelope.to_agent == "domain_analyst"
    assert json.loads(fields["data"])["assigned_to"] == "domain_analyst"


async def test_router_respects_unmet_dependencies():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    router = make_router(redis, max_concurrent=2)

    state = {
        "project_id": "proj-1",
        "tasks": [
            {"id": "t1", "name": "first", "assigned_to": "domain_analyst", "depends_on": []},
            {"id": "t2", "name": "second", "assigned_to": "domain_analyst", "depends_on": ["t1"]},
        ],
        "dispatched_task_ids": [],
    }
    updated = await router(state)

    # Only t1 is dispatchable on this pass.
    assert updated["dispatched_task_ids"] == ["t1"]
    entries = await redis.xrange("agent:domain_analyst:tasks")
    assert len(entries) == 1
