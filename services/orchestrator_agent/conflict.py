"""Conflict detection and escalation.

Sprint 2 ships a deterministic conflict checker rather than the LLM debate
loop from the spec — debate is an optional follow-on. The checker fires when
the Compliance Officer returns REJECTED while any other agent returned an
approving/completed status, or when the risk_level is RED.

Escalations are written to Postgres via `audit()` and republished on a
dedicated `orchestrator:escalations` stream so the UI can surface them.
"""
from __future__ import annotations

import logging
from typing import Any

import asyncpg
import redis.asyncio as aioredis

from libs.communication import (
    AgentMessage,
    ComplianceVerdict,
    MessageStatus,
    MessageType,
    RiskLevel,
)
from libs.communication.postgres_client import audit
from libs.communication.redis_client import publish
from services.orchestrator_agent.state import ConflictRecord, OrchestratorState

logger = logging.getLogger(__name__)

ESCALATION_STREAM = "orchestrator:escalations"
ORCHESTRATOR_AGENT_ID = "orchestrator-v1"


def detect_conflicts(state: OrchestratorState) -> list[ConflictRecord]:
    """Inspect collected results and surface contradictions.

    Rules (all checked):
      1. Any compliance result with verdict == REJECTED is itself a conflict
         the orchestrator must escalate.
      2. Any compliance result with risk_level == RED escalates.
      3. If compliance is REJECTED but another agent on the same project
         returned a completed/approving result, record it as a cross-agent
         conflict naming both sides.
    """
    results = state.get("results", {})
    if not results:
        return []

    conflicts: list[ConflictRecord] = []
    compliance_rejections: list[tuple[str, dict[str, Any]]] = []

    for task_id, payload in results.items():
        verdict = payload.get("verdict")
        risk = payload.get("risk_level")
        if verdict == ComplianceVerdict.REJECTED.value or risk == RiskLevel.RED.value:
            compliance_rejections.append((task_id, payload))
            conflicts.append(
                ConflictRecord(
                    type="compliance_rejection",
                    agent_a="compliance_officer",
                    agent_b="",
                    task_id_a=task_id,
                    task_id_b="",
                    rationale_a=str(payload.get("rationale", "")),
                    rationale_b="",
                )
            )

    if compliance_rejections:
        for task_id, payload in results.items():
            if (task_id, payload) in compliance_rejections:
                continue
            if payload.get("status") in {"completed", MessageStatus.COMPLETED.value}:
                rej_task, rej_payload = compliance_rejections[0]
                conflicts.append(
                    ConflictRecord(
                        type="approval_conflict",
                        agent_a="compliance_officer",
                        agent_b=str(payload.get("agent_id", "unknown")),
                        task_id_a=rej_task,
                        task_id_b=task_id,
                        rationale_a=str(rej_payload.get("rationale", "")),
                        rationale_b=str(payload.get("rationale", "")),
                    )
                )
    return conflicts


def make_conflict_resolver(
    redis_client: aioredis.Redis,
    pg_pool: asyncpg.Pool | None = None,
):
    """Returns a node that runs detect_conflicts, escalates, and updates state."""

    async def conflict_resolver(state: OrchestratorState) -> dict[str, Any]:
        conflicts = detect_conflicts(state)
        if not conflicts:
            return {"conflicts": [], "escalated": False, "current_phase": "done"}

        project_id = state.get("project_id", "unknown")
        for conflict in conflicts:
            envelope = AgentMessage(
                from_agent=ORCHESTRATOR_AGENT_ID,
                to_agent="human-reviewer",
                task_id=conflict.get("task_id_a", ""),
                message_type=MessageType.ESCALATION,
                status=MessageStatus.PENDING,
                data=dict(conflict),
                metadata={"project_id": project_id},
            )
            await publish(redis_client, ESCALATION_STREAM, envelope.to_stream_fields())
            if pg_pool is not None:
                await audit(
                    pg_pool,
                    agent_id=ORCHESTRATOR_AGENT_ID,
                    message_id=envelope.message_id,
                    task_id=envelope.task_id,
                    direction="out",
                    message_type=envelope.message_type.value,
                    status=envelope.status.value,
                    payload=dict(conflict),
                )
            logger.warning("Escalated conflict: %s", conflict.get("type"))

        return {
            "conflicts": conflicts,
            "escalated": True,
            "current_phase": "done",
        }

    return conflict_resolver
