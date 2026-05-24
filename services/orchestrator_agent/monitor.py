"""Result collection from per-orchestrator reply stream.

Specialist agents publish their results back on a single orchestrator reply
stream (default `orchestrator:replies`). The monitor reads until either:
  - every dispatched task is accounted for, or
  - the per-invocation timeout elapses.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import redis.asyncio as aioredis

from libs.communication import AgentMessage
from services.orchestrator_agent.state import OrchestratorState

logger = logging.getLogger(__name__)


def make_monitor(
    redis_client: aioredis.Redis,
    reply_stream: str = "orchestrator:replies",
    timeout_seconds: float = 60.0,
    poll_block_ms: int = 1000,
):
    """Build the monitor node bound to Redis."""

    async def monitor(state: OrchestratorState) -> dict[str, Any]:
        dispatched = set(state.get("dispatched_task_ids", []))
        results: dict[str, dict[str, Any]] = dict(state.get("results", {}))
        last_id = "$"  # only new messages from now
        deadline = asyncio.get_event_loop().time() + timeout_seconds

        while dispatched - results.keys():
            remaining = max(0.0, deadline - asyncio.get_event_loop().time())
            if remaining == 0.0:
                break
            entries = await redis_client.xread(
                {reply_stream: last_id},
                count=50,
                block=min(poll_block_ms, int(remaining * 1000)),
            )
            for _, messages in entries or []:
                for msg_id, fields in messages:
                    last_id = msg_id
                    try:
                        envelope = AgentMessage.from_stream_fields(fields)
                    except Exception:
                        logger.exception("Skipping malformed reply %s", msg_id)
                        continue
                    if envelope.task_id in dispatched:
                        results[envelope.task_id] = envelope.data

        timed_out = sorted(dispatched - results.keys())
        if timed_out:
            logger.warning("Monitor timed out waiting for %s", timed_out)

        return {
            "results": results,
            "timed_out_task_ids": timed_out,
            "current_phase": "resolving",
        }

    return monitor
