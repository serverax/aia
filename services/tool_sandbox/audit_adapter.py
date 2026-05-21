"""Bridge between `ToolRegistry.AuditSink` and the existing audit_log table.

The Postgres `audit_log` table (Sprint 1) was designed for inter-agent
message auditing — its columns are (agent_id, message_id, task_id,
direction, message_type, status, payload). Tool calls reuse the same
table with these mappings:

  agent_id     -> the agent that invoked the tool
  message_id   -> generated UUID for the tool call
  task_id      -> "{tool_name}:{tool_version}" (tool calls don't have task_ids)
  direction    -> 'tool'    (NEW value; existing rows used 'in'/'out' only)
  message_type -> 'tool_call'
  status       -> 'ok' | 'error'
  payload      -> { input_sha256, output_sha256, error?, ... }

We deliberately store hashes of input/output rather than the raw payloads:
tool inputs/outputs can be large (e.g. document text) and the audit log
isn't the right place for them. If full payload retention is needed for
compliance, that gets its own table in Sprint 7.

NOTE: the existing `audit_log.direction CHECK` constraint allows only
'in' and 'out'. Adding 'tool' requires an ALTER TABLE migration:

    ALTER TABLE audit_log DROP CONSTRAINT audit_log_direction_check;
    ALTER TABLE audit_log ADD CONSTRAINT audit_log_direction_check
        CHECK (direction IN ('in', 'out', 'tool'));

The migration script is at infrastructure/k3s/migrations/0002_audit_tool.sql.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any, Mapping

import asyncpg

from libs.communication.postgres_client import audit

logger = logging.getLogger(__name__)


def _digest(payload: Mapping[str, Any] | None) -> str:
    """Stable SHA-256 over a JSON-canonical form of payload."""
    if not payload:
        return "0" * 64
    encoded = json.dumps(dict(payload), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class PostgresToolAuditSink:
    """Writes one row per tool invocation into audit_log."""

    def __init__(self, pool: asyncpg.Pool, default_agent_id: str = "unknown") -> None:
        self._pool = pool
        # Held only as a fallback when the caller doesn't supply agent_id.
        self._default_agent_id = default_agent_id

    async def record(
        self,
        *,
        agent_id: str,
        tool_name: str,
        tool_version: str,
        status: str,
        input_payload: Mapping[str, Any],
        output_payload: Mapping[str, Any],
        error: str | None,
    ) -> None:
        message_id = str(uuid.uuid4())
        task_id = f"{tool_name}:{tool_version}"
        digest_payload = {
            "tool_name": tool_name,
            "tool_version": tool_version,
            "input_sha256": _digest(input_payload),
            "output_sha256": _digest(output_payload),
            "error": error,
        }
        try:
            await audit(
                self._pool,
                agent_id=agent_id or self._default_agent_id,
                message_id=message_id,
                task_id=task_id,
                direction="tool",
                message_type="tool_call",
                status=status,
                payload=digest_payload,
            )
        except Exception:
            # Auditing must never sink the actual tool call. Log + swallow.
            logger.exception(
                "audit write failed for agent=%s tool=%s (call still succeeded)",
                agent_id, tool_name,
            )
