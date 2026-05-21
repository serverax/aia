"""Unit tests for Orchestrator nodes with a StubLLMClient."""
from __future__ import annotations

import pytest

from libs.llm import StubLLMClient
from services.orchestrator_agent.nodes import (
    conflict_branch,
    make_intent_parser,
    make_task_decomposer,
    should_continue,
)

pytestmark = [pytest.mark.unit]


async def test_intent_parser_records_clarification_flag():
    stub = StubLLMClient([
        {
            "objective": "Draft a settlement agreement",
            "domain": "employment_law",
            "scope": "UK",
            "constraints": [],
            "ambiguities": [],
            "requires_clarification": False,
            "clarification_questions": [],
        }
    ])
    node = make_intent_parser(stub)
    state = await node({"user_request": "Draft a settlement agreement"})

    assert state["intent"]["domain"] == "employment_law"
    assert state["requires_clarification"] is False
    assert state["current_phase"] == "decomposing"


async def test_intent_parser_routes_to_clarification_when_ambiguous():
    stub = StubLLMClient([
        {
            "objective": "?",
            "domain": "general",
            "scope": "?",
            "constraints": [],
            "ambiguities": ["jurisdiction", "claim type"],
            "requires_clarification": True,
            "clarification_questions": ["What jurisdiction?"],
        }
    ])
    node = make_intent_parser(stub)
    state = await node({"user_request": "Help with my case"})
    assert state["requires_clarification"] is True
    assert state["current_phase"] == "awaiting_clarification"
    assert should_continue(state) == "clarify"


async def test_task_decomposer_builds_typed_tasks():
    stub = StubLLMClient([
        {
            "tasks": [
                {
                    "id": "task_1",
                    "name": "Research precedent",
                    "description": "Find 3 similar cases",
                    "assigned_to": "domain_analyst",
                    "inputs": {},
                    "expected_outputs": ["case_list"],
                    "depends_on": [],
                    "priority": "high",
                    "deadline": None,
                },
                {
                    "id": "task_2",
                    "name": "Compliance check",
                    "description": "Verify GDPR",
                    "assigned_to": "compliance_officer",
                    "inputs": {},
                    "expected_outputs": ["verdict"],
                    "depends_on": ["task_1"],
                    "priority": "critical",
                    "deadline": None,
                },
            ]
        }
    ])
    node = make_task_decomposer(stub)
    state = await node({
        "intent": {"objective": "Draft agreement", "domain": "employment_law", "constraints": []},
        "requires_clarification": False,
    })
    assert state["current_phase"] == "dispatching"
    assert len(state["tasks"]) == 2
    assert state["tasks"][0]["assigned_to"] == "domain_analyst"
    assert state["tasks"][1]["depends_on"] == ["task_1"]


async def test_task_decomposer_skips_when_clarification_needed():
    stub = StubLLMClient([])  # Should never call LLM
    node = make_task_decomposer(stub)
    state = await node({"requires_clarification": True})
    assert state["tasks"] == []
    assert state["current_phase"] == "awaiting_clarification"
    assert stub.calls == []


def test_conflict_branch_escalates_on_recorded_conflict():
    assert conflict_branch({"conflicts": [{"type": "x"}]}) == "escalate"
    assert conflict_branch({"escalated": True}) == "escalate"
    assert conflict_branch({"conflicts": [], "escalated": False}) == "complete"
