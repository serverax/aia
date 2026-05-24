"""Unit tests for the Analyst Agent's tool-use integration.

We drive the agent's `_handle()` method with a forged Redis-stream-fields
dict, a StubLLMClient seeded with tool_use responses, and a fake tool
executor injected by overriding `tool_registry`. No Redis, no Postgres,
no real WASM — just verifies the wiring between the agent loop and the
tool registry surface.
"""

from __future__ import annotations

from typing import Any

import pytest

from libs.communication import AgentMessage, MessageStatus, MessageType
from libs.llm import AssistantResponse, StubLLMClient, TextBlock, ToolUseBlock
from services.analyst_agent.main import AnalystAgent, Settings

pytestmark = [pytest.mark.unit]


class _FakeTool:
    name = "parse_dates_v3"
    description = "extract dates"
    input_schema = {"type": "object"}


class _FakeRegistry:
    """ToolRegistry stand-in for unit tests."""

    def __init__(self, calls: list):
        self._tool = _FakeTool()
        self._calls = calls

    def names(self):
        return [self._tool.name]

    def is_allowed(self, agent_id: str, tool_name: str) -> bool:
        return True

    def get(self, name: str):
        return self._tool

    async def execute(self, agent_id: str, tool_name: str, input_payload: dict[str, Any]):
        self._calls.append((agent_id, tool_name, input_payload))
        return {"dates": [{"iso": "2026-05-21", "raw": "2026-05-21", "confidence": 0.98}]}


def _build_agent(stub_llm: StubLLMClient, tool_calls: list) -> AnalystAgent:
    settings = Settings(agent_id="analyst-test", audit_enabled=False)
    agent = AnalystAgent.__new__(AnalystAgent)
    agent.settings = settings
    agent.tracer = None  # _handle uses tracer via a context-manager; we patch below
    agent.redis = None
    agent.pg_pool = None
    agent.llm = stub_llm
    agent.tool_registry = _FakeRegistry(tool_calls)
    import asyncio

    agent._stop = asyncio.Event()
    return agent


@pytest.fixture
def patch_tracer(monkeypatch):
    """The real `init_telemetry` returns an OTel tracer. For these tests we
    swap in a no-op context manager so `_handle` doesn't error on `agent.tracer.start_as_current_span`.
    """
    from contextlib import nullcontext

    class _Span:
        def set_attribute(self, *_a, **_k):
            pass

        def record_exception(self, *_a, **_k):
            pass

        def set_status(self, *_a, **_k):
            pass

    class _Tracer:
        def start_as_current_span(self, *_a, **_k):
            return _ContextSpan()

    class _ContextSpan:
        def __enter__(self):
            return _Span()

        def __exit__(self, *_):
            return False

    return _Tracer()


def test_tool_descriptors_for_agent_filters_by_acl():
    stub = StubLLMClient()
    agent = _build_agent(stub, tool_calls=[])
    tools = agent._tool_descriptors_for_agent()
    assert [t.name for t in tools] == ["parse_dates_v3"]


async def test_handle_invokes_agent_loop_and_publishes_reply(monkeypatch, patch_tracer):
    """Full path: incoming message → agent_loop → tool call → reply publish.

    We patch out the Redis publish + audit calls (since redis/pg are None) by
    monkeypatching the symbols inside services.analyst_agent.main.
    """
    published: list[tuple[str, dict]] = []
    acked: list[str] = []

    async def fake_publish(client, stream, fields, **kw):
        published.append((stream, fields))
        return "fake-id"

    async def fake_ack(client, stream, group, message_id):
        acked.append(message_id)

    import services.analyst_agent.main as mod

    monkeypatch.setattr(mod, "publish", fake_publish)
    monkeypatch.setattr(mod, "ack", fake_ack)

    stub = StubLLMClient(
        tool_responses=[
            AssistantResponse(
                blocks=[
                    ToolUseBlock(id="u1", name="parse_dates_v3", input={"text": "due 2026-05-21"})
                ],
                stop_reason="tool_use",
            ),
            AssistantResponse(
                blocks=[TextBlock(text="The date is 2026-05-21 per parse_dates_v3.")],
                stop_reason="end_turn",
            ),
        ]
    )
    tool_call_log: list = []
    agent = _build_agent(stub, tool_calls=tool_call_log)
    agent.tracer = patch_tracer

    incoming = AgentMessage(
        from_agent="orchestrator-v1",
        to_agent="domain_analyst",
        task_id="t-1",
        message_type=MessageType.TASK_ASSIGNMENT,
        status=MessageStatus.IN_PROGRESS,
        data={"description": "Find dates in: due 2026-05-21"},
    )
    await agent._handle("redis-id-1", incoming.to_stream_fields())

    assert tool_call_log == [("analyst-test", "parse_dates_v3", {"text": "due 2026-05-21"})]
    assert len(published) == 1
    stream, fields = published[0]
    assert stream == agent.settings.reply_stream
    reply = AgentMessage.from_stream_fields(fields)
    assert reply.task_id == "t-1"
    assert "2026-05-21" in reply.data["output"]
    assert acked == ["redis-id-1"]
