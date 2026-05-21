"""Task routing onto Redis Streams.

The router walks the decomposed task list, respects `depends_on`, and
dispatches ready tasks to the per-agent input stream. A semaphore caps
concurrent XADDs so a runaway decomposition can't flood the broker.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import redis.asyncio as aioredis

from libs.communication import AgentMessage, MessageStatus, MessageType, TaskAssignment
from libs.communication.redis_client import publish
from services.orchestrator_agent.state import OrchestratorState, TaskSpec

logger = logging.getLogger(__name__)

ORCHESTRATOR_AGENT_ID = "orchestrator-v1"


def _stream_for(assigned_to: str) -> str:
    """Return the Redis Stream this agent type listens on."""
    return f"agent:{assigned_to}:tasks"


def _ready(task: TaskSpec, completed_ids: set[str]) -> bool:
    return all(dep in completed_ids for dep in task.get("depends_on", []))


def make_router(
    redis_client: aioredis.Redis,
    max_concurrent: int = 20,
):
    """Build the router node bound to a Redis client.

    Returns a coroutine that, given the current OrchestratorState, dispatches
    every ready task once and records the dispatched task_ids.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _dispatch_one(task: TaskSpec, project_id: str) -> str:
        async with semaphore:
            assignment = TaskAssignment(
                task_id=task["id"],
                name=task.get("name", ""),
                description=task.get("description", ""),
                assigned_to=task["assigned_to"],
                inputs=task.get("inputs", {}),
                expected_outputs=task.get("expected_outputs", []),
                project_id=project_id,
                priority=task.get("priority", "normal"),
                deadline=task.get("deadline"),
            )
            envelope = AgentMessage(
                from_agent=ORCHESTRATOR_AGENT_ID,
                to_agent=task["assigned_to"],
                task_id=task["id"],
                message_type=MessageType.TASK_ASSIGNMENT,
                status=MessageStatus.IN_PROGRESS,
                data=assignment.model_dump(),
                metadata={"project_id": project_id},
            )
            await publish(redis_client, _stream_for(task["assigned_to"]), envelope.to_stream_fields())
            logger.info(
                "Dispatched task %s to %s (project %s)",
                task["id"],
                task["assigned_to"],
                project_id,
            )
            return task["id"]

    async def router(state: OrchestratorState) -> dict[str, Any]:
        tasks: list[TaskSpec] = state.get("tasks", [])
        project_id = state["project_id"]
        completed = set(state.get("dispatched_task_ids", []))

        dispatchable = [t for t in tasks if t["id"] not in completed and _ready(t, completed)]
        if not dispatchable:
            return {"current_phase": "monitoring"}

        new_ids = await asyncio.gather(
            *[_dispatch_one(t, project_id) for t in dispatchable]
        )
        return {
            "dispatched_task_ids": list(completed.union(new_ids)),
            "current_phase": "monitoring",
        }

    return router
