"""LangGraph nodes for the Orchestrator.

Each node takes the current OrchestratorState and returns a partial dict
of state updates. LLM access is injected via closure (see graph.py).
"""
from __future__ import annotations

import logging
from typing import Any

from libs.llm import LLMClient
from services.orchestrator_agent.prompts import DECOMPOSE_PROMPT, INTENT_PROMPT
from services.orchestrator_agent.state import OrchestratorState, TaskSpec

logger = logging.getLogger(__name__)


def make_intent_parser(llm: LLMClient):
    """Build the intent_parser node bound to a specific LLM client."""

    async def intent_parser(state: OrchestratorState) -> dict[str, Any]:
        prompt = INTENT_PROMPT.format(user_request=state["user_request"])
        intent = await llm.chat_json(prompt)
        requires_clarification = bool(intent.get("requires_clarification", False))
        return {
            "intent": intent,
            "requires_clarification": requires_clarification,
            "clarification_questions": intent.get("clarification_questions", []),
            "current_phase": (
                "awaiting_clarification" if requires_clarification else "decomposing"
            ),
        }

    return intent_parser


def make_task_decomposer(llm: LLMClient):
    async def task_decomposer(state: OrchestratorState) -> dict[str, Any]:
        if state.get("requires_clarification"):
            # Skip decomposition; the orchestrator will return clarification questions.
            return {"tasks": [], "current_phase": "awaiting_clarification"}

        intent = state["intent"]
        prompt = DECOMPOSE_PROMPT.format(
            objective=intent.get("objective", ""),
            domain=intent.get("domain", "general"),
            constraints=intent.get("constraints", []),
        )
        result = await llm.chat_json(prompt)
        raw_tasks = result.get("tasks") or []
        tasks: list[TaskSpec] = []
        for raw in raw_tasks:
            tasks.append(
                TaskSpec(
                    id=raw.get("id") or f"task_{len(tasks) + 1}",
                    name=raw.get("name", ""),
                    description=raw.get("description", ""),
                    assigned_to=raw.get("assigned_to", "domain_analyst"),
                    inputs=raw.get("inputs", {}),
                    expected_outputs=raw.get("expected_outputs", []),
                    depends_on=raw.get("depends_on", []),
                    priority=raw.get("priority", "normal"),
                    deadline=raw.get("deadline"),
                )
            )
        return {"tasks": tasks, "current_phase": "dispatching"}

    return task_decomposer


def should_continue(state: OrchestratorState) -> str:
    """Conditional edge after intent parsing.

    If the LLM said the request is ambiguous, end the graph and let the
    caller surface clarification questions. Otherwise proceed to decompose.
    """
    return "clarify" if state.get("requires_clarification") else "decompose"


def conflict_branch(state: OrchestratorState) -> str:
    """Conditional edge after monitoring.

    If any conflict was recorded OR any task explicitly returned a
    REJECTED verdict, escalate. Otherwise complete normally.
    """
    if state.get("escalated"):
        return "escalate"
    if state.get("conflicts"):
        return "escalate"
    return "complete"
