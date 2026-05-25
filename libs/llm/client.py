"""Thin LLM abstraction.

Sprint 2 nodes need to call Claude for intent parsing and task
decomposition, but unit tests must run without an API key. We define a
`LLMClient` Protocol and ship two implementations:

  - `AnthropicClient` wraps `langchain_anthropic.ChatAnthropic`.
  - `StubLLMClient` returns canned JSON responses in order.

`build_default_client()` returns the real client if `ANTHROPIC_API_KEY` is
set in the environment, otherwise raises — call sites should handle the
fallback explicitly so a missing key never silently degrades to stubs in
production.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    """Minimum surface every node depends on."""

    async def chat_json(self, prompt: str) -> dict[str, Any]:
        """Send a prompt that expects a single JSON object back.

        Implementations should strip code fences and parse the response.
        Raise `ValueError` if the response cannot be parsed as JSON.
        """
        ...


class AnthropicClient:
    """Real Claude client via langchain-anthropic."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        # Import lazily so that test environments without langchain-anthropic
        # installed (e.g. CI for unit-only runs) don't fail at import time.
        from langchain_anthropic import ChatAnthropic

        self._llm = ChatAnthropic(
            model=model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            anthropic_api_key=api_key or os.environ["ANTHROPIC_API_KEY"],
            temperature=temperature,
        )

    async def chat_json(self, prompt: str) -> dict[str, Any]:
        # langchain's `ainvoke` returns an AIMessage; `.content` is a string.
        message = await self._llm.ainvoke(prompt)
        text = message.content if isinstance(message.content, str) else str(message.content)
        return _parse_json(text)

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
    ):
        """Tool-use chat via the Anthropic SDK directly.

        We bypass langchain here because langchain's tool abstraction
        adds an extra translation layer that loses the raw tool_use
        blocks we need to feed to ToolRegistry.execute().
        """
        from anthropic import AsyncAnthropic

        from libs.llm.tools import AssistantResponse, TextBlock, ToolUseBlock

        client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        response = await client.messages.create(
            model=model,
            system=system or "",
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
        )
        blocks: list[TextBlock | ToolUseBlock] = []
        for block in response.content:
            if block.type == "text":
                blocks.append(TextBlock(text=block.text))
            elif block.type == "tool_use":
                blocks.append(ToolUseBlock(id=block.id, name=block.name, input=block.input))
        return AssistantResponse(blocks=blocks, stop_reason=response.stop_reason or "end_turn")


class StubLLMClient:
    """Returns pre-baked responses in order.

    Two queues: `responses` for `chat_json` (Sprint 2 nodes) and
    `tool_responses` for `chat_with_tools` (Sprint 6 agent_loop). Both
    are independent — a test that only uses one can ignore the other.

    Usage:

        # Sprint 2 style
        stub = StubLLMClient(responses=[{"objective": "x"}])

        # Sprint 6 style with tool_use
        from libs.llm.tools import AssistantResponse, ToolUseBlock, TextBlock
        stub = StubLLMClient(tool_responses=[
            AssistantResponse(
                blocks=[ToolUseBlock(id="u1", name="parse_dates_v3", input={"text": "hi"})],
                stop_reason="tool_use",
            ),
            AssistantResponse(
                blocks=[TextBlock(text="Done.")],
                stop_reason="end_turn",
            ),
        ])
    """

    def __init__(
        self,
        responses: list[dict[str, Any]] | None = None,
        tool_responses: list[Any] | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._tool_responses = list(tool_responses or [])
        self.calls: list[str] = []
        self.tool_calls: list[dict[str, Any]] = []

    async def chat_json(self, prompt: str) -> dict[str, Any]:
        self.calls.append(prompt)
        if not self._responses:
            raise RuntimeError("StubLLMClient.chat_json exhausted")
        return self._responses.pop(0)

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
    ):
        import copy

        # Snapshot inputs — agent_loop reuses the same `messages` list across
        # iterations and mutates it in place. Without a deep copy, the stub's
        # tool_calls history all points at the final mutated state.
        self.tool_calls.append(
            {
                "messages": copy.deepcopy(messages),
                "tools": copy.deepcopy(tools),
                "system": system,
            }
        )
        if not self._tool_responses:
            raise RuntimeError("StubLLMClient.chat_with_tools exhausted")
        return self._tool_responses.pop(0)


def build_default_client() -> LLMClient:
    """Return an Anthropic client. Raises if ANTHROPIC_API_KEY is missing."""
    if "ANTHROPIC_API_KEY" not in os.environ:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set; cannot build AnthropicClient. "
            "Set it in .env or inject a StubLLMClient for testing."
        )
    return AnthropicClient()


def _parse_json(text: str) -> dict[str, Any]:
    """Best-effort JSON parse from an LLM response.

    Strips common markdown fences and leading/trailing prose. If the model
    wrapped the JSON in ```json fences, drop those. If parsing still fails,
    raise `ValueError`.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response is not valid JSON: {exc.msg}: {text[:200]!r}") from exc
