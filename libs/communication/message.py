"""Typed message schemas for inter-agent communication.

`protocol.create_message` produces a plain dict shape used on the wire
(Redis Streams stores flat key/value pairs). This module adds Pydantic
models that validate and parse those dicts at agent boundaries so
services don't pass raw strings around.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    TASK_ASSIGNMENT = "task_assignment"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    HEARTBEAT = "heartbeat"
    ESCALATION = "escalation"
    ECHO = "echo"


class MessageStatus(str, Enum):
    """Envelope-level processing state."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ComplianceVerdict(str, Enum):
    """Domain decision from the Compliance Officer agent.

    Separate from MessageStatus: the envelope can be COMPLETED while the
    verdict inside is REJECTED.
    """

    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REVISION = "requires_revision"
    REQUIRES_HUMAN = "requires_human"


class RiskLevel(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class AgentMessage(BaseModel):
    """Envelope for any message exchanged between agents."""

    message_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    from_agent: str
    to_agent: str
    task_id: str
    message_type: MessageType
    status: MessageStatus
    data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_stream_fields(self) -> dict[str, str]:
        """Flatten for XADD. Redis Streams store flat string fields, so
        nested objects are JSON-encoded under the same key."""
        import json

        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "task_id": self.task_id,
            "message_type": self.message_type.value,
            "status": self.status.value,
            "data": json.dumps(self.data),
            "metadata": json.dumps(self.metadata),
        }

    @classmethod
    def from_stream_fields(cls, fields: dict[str, str]) -> "AgentMessage":
        """Inverse of to_stream_fields. Tolerant of missing optional fields."""
        import json

        return cls(
            message_id=fields.get("message_id", str(uuid4())),
            timestamp=fields.get(
                "timestamp",
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            ),
            from_agent=fields["from_agent"],
            to_agent=fields["to_agent"],
            task_id=fields["task_id"],
            message_type=MessageType(fields["message_type"]),
            status=MessageStatus(fields["status"]),
            data=json.loads(fields.get("data") or "{}"),
            metadata=json.loads(fields.get("metadata") or "{}"),
        )


class TaskAssignment(BaseModel):
    """Payload an Orchestrator sends to a specialist agent."""

    task_id: str
    name: str
    description: str
    assigned_to: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list)
    project_id: str
    priority: str = "normal"
    deadline: str | None = None


class TaskResult(BaseModel):
    """Payload a specialist agent sends back on completion."""

    task_id: str
    project_id: str
    agent_id: str
    status: MessageStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ComplianceResult(BaseModel):
    """Domain payload returned by the Compliance Officer.

    The orchestrator inspects `verdict` + `risk_level` for conflict
    detection. Flags carry the specific regulations or clauses triggered.
    """

    task_id: str
    verdict: ComplianceVerdict
    risk_level: RiskLevel
    flags: list[str] = Field(default_factory=list)
    rationale: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
