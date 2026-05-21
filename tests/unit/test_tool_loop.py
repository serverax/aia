"""Unit tests for the Claude tool-use loop.

Uses StubLLMClient with canned AssistantResponse sequences; a hand-rolled
async tool_executor stands in for `ToolRegistry.execute`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from libs.llm import (
    AssistantResponse,
    StubLLMClient,
    TextBlock,
    ToolUseBlock,
    agent_loop,
    to_anthropic_spec,
)

pytestmark = [pytest.mark.unit]


@dataclass
class _FakeDescriptor:
    name: str
    description: str
    input_schema: dict[str, Any]


def _executor_factory():
    """Async tool_executor that records every call."""
    log: list[tuple[str, str, dict]] = []

    async def execute(agent_id: str, tool_name: str, input_payload: dict[str, Any]):
        log.append((agent_id, tool_name, input_payload))
        # Simulate the tool returning something useful.
        return {"echoed": input_payload}

    return execute, log


def test_to_anthropic_spec_round_trip():
    desc = _FakeDescriptor(
        name="parse_dates_v3",
        description="Extract dates",
        input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
    )
    spec = to_anthropic_spec(desc)
    assert spec == {
        "name": "parse_dates_v3",
        "description": "Extract dates",
        "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}},
    }


async def test_agent_loop_terminates_when_no_tool_use():
    stub = StubLLMClient(tool_responses=[
        AssistantResponse(
            blocks=[TextBlock(text="Just text, no tools.")],
            stop_reason="end_turn",
        )
    ])
    executor, log = _executor_factory()
    response = await agent_loop(
        llm=stub,
        agent_id="analyst",
        initial_messages=[{"role": "user", "content": "Hi"}],
        tool_descriptors=[],
        tool_executor=executor,
    )
    assert response.text == "Just text, no tools."
    assert log == []
    assert len(stub.tool_calls) == 1


async def test_agent_loop_runs_one_tool_then_completes():
    desc = _FakeDescriptor(
        name="parse_dates_v3",
        description="extract dates",
        input_schema={"type": "object"},
    )
    stub = StubLLMClient(tool_responses=[
        AssistantResponse(
            blocks=[ToolUseBlock(id="u1", name="parse_dates_v3", input={"text": "due 2026-05-21"})],
            stop_reason="tool_use",
        ),
        AssistantResponse(
            blocks=[TextBlock(text="Found one date.")],
            stop_reason="end_turn",
        ),
    ])
    executor, log = _executor_factory()
    response = await agent_loop(
        llm=stub,
        agent_id="analyst",
        initial_messages=[{"role": "user", "content": "What dates appear in: due 2026-05-21?"}],
        tool_descriptors=[desc],
        tool_executor=executor,
    )
    assert response.text == "Found one date."
    assert log == [("analyst", "parse_dates_v3", {"text": "due 2026-05-21"})]
    # Two LLM round trips: initial + after tool result
    assert len(stub.tool_calls) == 2

    # The second LLM call's messages should include both the assistant's
    # tool_use AND a user tool_result.
    second_call_msgs = stub.tool_calls[1]["messages"]
    assert any(m["role"] == "assistant" for m in second_call_msgs)
    last = second_call_msgs[-1]
    assert last["role"] == "user"
    assert last["content"][0]["type"] == "tool_result"
    assert last["content"][0]["tool_use_id"] == "u1"
    assert json.loads(last["content"][0]["content"]) == {"echoed": {"text": "due 2026-05-21"}}


async def test_agent_loop_runs_multiple_tools_in_one_turn():
    """Claude can emit several tool_use blocks per response; loop must run all."""
    desc1 = _FakeDescriptor(name="tool_a", description="a", input_schema={"type": "object"})
    desc2 = _FakeDescriptor(name="tool_b", description="b", input_schema={"type": "object"})
    stub = StubLLMClient(tool_responses=[
        AssistantResponse(
            blocks=[
                ToolUseBlock(id="u1", name="tool_a", input={"x": 1}),
                ToolUseBlock(id="u2", name="tool_b", input={"y": 2}),
            ],
            stop_reason="tool_use",
        ),
        AssistantResponse(
            blocks=[TextBlock(text="Combined.")],
            stop_reason="end_turn",
        ),
    ])
    executor, log = _executor_factory()
    response = await agent_loop(
        llm=stub,
        agent_id="analyst",
        initial_messages=[{"role": "user", "content": "Do both."}],
        tool_descriptors=[desc1, desc2],
        tool_executor=executor,
    )
    assert response.text == "Combined."
    assert [c[1] for c in log] == ["tool_a", "tool_b"]


async def test_agent_loop_captures_tool_errors_as_tool_result_is_error():
    desc = _FakeDescriptor(name="brittle", description="", input_schema={"type": "object"})

    async def failing_executor(agent_id, tool_name, input_payload):
        raise PermissionError(f"agent {agent_id} cannot call {tool_name}")

    stub = StubLLMClient(tool_responses=[
        AssistantResponse(
            blocks=[ToolUseBlock(id="u1", name="brittle", input={})],
            stop_reason="tool_use",
        ),
        AssistantResponse(
            blocks=[TextBlock(text="Recovered.")],
            stop_reason="end_turn",
        ),
    ])
    response = await agent_loop(
        llm=stub,
        agent_id="analyst",
        initial_messages=[{"role": "user", "content": "Try."}],
        tool_descriptors=[desc],
        tool_executor=failing_executor,
    )
    assert response.text == "Recovered."
    # The tool result sent back to the LLM should flag is_error
    second_call_msgs = stub.tool_calls[1]["messages"]
    err_block = second_call_msgs[-1]["content"][0]
    assert err_block["is_error"] is True
    assert "cannot call" in err_block["content"]


async def test_agent_loop_respects_max_iterations():
    """If Claude keeps asking for tools forever, the loop bails out."""
    desc = _FakeDescriptor(name="t", description="", input_schema={"type": "object"})

    # Build N+1 responses, all asking for the tool again.
    stub = StubLLMClient(tool_responses=[
        AssistantResponse(
            blocks=[ToolUseBlock(id=f"u{i}", name="t", input={})],
            stop_reason="tool_use",
        )
        for i in range(5)
    ])
    executor, log = _executor_factory()
    response = await agent_loop(
        llm=stub,
        agent_id="analyst",
        initial_messages=[{"role": "user", "content": "Loop!"}],
        tool_descriptors=[desc],
        tool_executor=executor,
        max_iterations=3,
    )
    # The loop returned the LAST assistant response it saw (still tool_use,
    # but we surface it rather than spinning forever).
    assert response.stop_reason == "tool_use"
    assert len(log) == 3  # max_iterations
