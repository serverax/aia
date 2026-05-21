"""LangGraph state for the Orchestrator.

LangGraph nodes take a state dict and return a partial-update dict. The
state is a TypedDict so static checking flags missing keys, but at runtime
nodes can omit keys they don't touch and LangGraph will merge them.
"""
from __future__ import annotations

from typing import Any, TypedDict


class TaskSpec(TypedDict, total=False):
    """A single decomposed task. Mirrors the LLM JSON schema."""

    id: str
    name: str
    description: str
    assigned_to: str           # "domain_analyst" | "compliance_officer" | "editor"
    inputs: dict[str, Any]
    expected_outputs: list[str]
    depends_on: list[str]
    priority: str              # "critical" | "high" | "normal"
    deadline: str | None       # ISO-8601 or None


class ConflictRecord(TypedDict, total=False):
    type: str
    agent_a: str
    agent_b: str
    task_id_a: str
    task_id_b: str
    rationale_a: str
    rationale_b: str


class OrchestratorState(TypedDict, total=False):
    """Single graph invocation's state."""

    # Inputs
    user_request: str
    project_id: str

    # Intent parsing
    intent: dict[str, Any]
    requires_clarification: bool
    clarification_questions: list[str]

    # Decomposition
    tasks: list[TaskSpec]

    # Dispatch / monitor
    current_phase: str         # "parsing" | "decomposing" | "dispatching" | "monitoring" | "resolving" | "done"
    dispatched_task_ids: list[str]
    results: dict[str, dict[str, Any]]   # task_id -> result payload
    timed_out_task_ids: list[str]

    # Conflicts
    conflicts: list[ConflictRecord]
    escalated: bool
