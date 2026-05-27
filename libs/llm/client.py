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


class OllamaToolUseUnsupportedError(RuntimeError):
    """Raised when tool-use is requested but the Ollama model isn't tool-capable.

    Lets the analyst's `chat_with_tools` path fail *loudly and safely* on a
    non-tool model instead of silently returning text that ignores the tools.
    Non-tool flows (`chat_json`, or `chat_with_tools` with an empty tool list)
    are unaffected.
    """


class OllamaClient:
    """LLM client backed by an in-cluster Ollama server (native /api/chat).

    Reads `OLLAMA_BASE_URL` and `OLLAMA_MODEL`. Never reads Anthropic creds, so
    the dev path works with no `ANTHROPIC_API_KEY`. httpx is imported lazily so
    importing this module stays cheap and offline.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        *,
        supports_tools: bool | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = (
            base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self._model = model or os.environ.get("OLLAMA_MODEL", "llama3.1")
        if supports_tools is None:
            supports_tools = os.environ.get("OLLAMA_SUPPORTS_TOOLS", "false").strip().lower() in (
                "1",
                "true",
                "yes",
            )
        self._supports_tools = supports_tools
        self._timeout = timeout
        # base_url/model are not secrets; no credentials are ever logged.
        logger.info(
            "OllamaClient configured (base_url=%s, model=%s, tools=%s)",
            self._base_url,
            self._model,
            self._supports_tools,
        )

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}{path}", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def chat_json(self, prompt: str) -> dict[str, Any]:
        data = await self._post(
            "/api/chat",
            {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "format": "json",
                "stream": False,
                "options": {"temperature": 0},
            },
        )
        content = data.get("message", {}).get("content", "")
        return _parse_json(content)

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
    ):
        from libs.llm.tools import AssistantResponse, TextBlock, ToolUseBlock

        if tools and not self._supports_tools:
            raise OllamaToolUseUnsupportedError(
                f"tool-use requested but Ollama model {self._model!r} is not configured "
                "as tool-capable. Set OLLAMA_SUPPORTS_TOOLS=true with a tool-capable model, "
                "or route tool-using agents to an Anthropic fallback."
            )

        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": msgs,
            "stream": False,
            "options": {"temperature": 0},
        }
        if tools:
            payload["tools"] = tools

        data = await self._post("/api/chat", payload)
        msg = data.get("message", {})
        blocks: list[TextBlock | ToolUseBlock] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            blocks.append(
                ToolUseBlock(
                    id=tc.get("id") or fn.get("name", ""),
                    name=fn.get("name", ""),
                    input=fn.get("arguments", {}) or {},
                )
            )
        text = msg.get("content") or ""
        if text:
            blocks.append(TextBlock(text=text))
        stop_reason = "tool_use" if any(isinstance(b, ToolUseBlock) for b in blocks) else "end_turn"
        return AssistantResponse(blocks=blocks, stop_reason=stop_reason)


def build_default_client() -> LLMClient:
    """Build the LLM client selected by `LLM_PROVIDER`.

    - `ollama`   -> `OllamaClient` (reads OLLAMA_BASE_URL/OLLAMA_MODEL; no
      Anthropic key required — the dev default).
    - `anthropic` (also the implicit default when LLM_PROVIDER is unset, for
      backward compatibility) -> `AnthropicClient`; raises if ANTHROPIC_API_KEY
      is missing.
    - anything else -> a clear error.
    """
    provider = os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()
    if provider == "ollama":
        return OllamaClient()
    if provider == "anthropic":
        if "ANTHROPIC_API_KEY" not in os.environ:
            raise RuntimeError(
                "LLM_PROVIDER=anthropic (or unset default) but ANTHROPIC_API_KEY is not set. "
                "Set LLM_PROVIDER=ollama for the dev path, or provide ANTHROPIC_API_KEY."
            )
        return AnthropicClient()
    raise RuntimeError(f"Unsupported LLM_PROVIDER={provider!r}; expected 'ollama' or 'anthropic'.")


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
