"""Tests for LLM provider selection + the Ollama client.

Covers the six guarantees required for the Ollama dev path:
  1. LLM_PROVIDER=ollama builds an Ollama client
  2. a missing ANTHROPIC_API_KEY does not break the Ollama path
  3. LLM_PROVIDER=anthropic still works when explicitly selected
  4. an unsupported provider fails clearly
  5. no API keys/secrets are logged
  6. tool-use on a non-tool Ollama model fails safely; non-tool flows still work

No live Ollama/Anthropic needed — HTTP and the Anthropic client are stubbed.
"""

from __future__ import annotations

import logging

import pytest

from libs.llm import client as llm_client
from libs.llm.client import OllamaClient, OllamaToolUseUnsupportedError, build_default_client

pytestmark = [pytest.mark.unit]


def test_provider_ollama_builds_ollama_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv(
        "OLLAMA_BASE_URL", "http://aia-ollama-dev-cpu.aia-dev.svc.cluster.local:11434"
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    c = build_default_client()
    assert isinstance(c, OllamaClient)


def test_ollama_path_ignores_missing_anthropic_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    # Must NOT raise even though there is no Anthropic key.
    assert isinstance(build_default_client(), OllamaClient)


def test_provider_anthropic_explicit(monkeypatch):
    sentinel = object()
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-DUMMY")
    # Stub AnthropicClient so the test doesn't need langchain-anthropic or a key.
    monkeypatch.setattr(llm_client, "AnthropicClient", lambda *a, **k: sentinel)

    assert build_default_client() is sentinel


def test_anthropic_default_still_requires_key(monkeypatch):
    # Backward-compat: unset provider defaults to anthropic and requires the key.
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY is not set"):
        build_default_client()


def test_unsupported_provider_fails_clearly(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gpt-5")
    with pytest.raises(RuntimeError, match="Unsupported LLM_PROVIDER"):
        build_default_client()


def test_no_secrets_logged(monkeypatch, caplog):
    secret = "sk-SUPER-SECRET-dummy-key-do-not-log"
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434")

    with caplog.at_level(logging.DEBUG):
        assert isinstance(build_default_client(), OllamaClient)

    assert secret not in caplog.text


@pytest.mark.asyncio
async def test_tool_use_unsupported_fails_safely():
    c = OllamaClient(base_url="http://ollama:11434", model="llama3.1", supports_tools=False)
    with pytest.raises(OllamaToolUseUnsupportedError):
        await c.chat_with_tools(
            messages=[{"role": "user", "content": "hi"}],
            tools=[{"type": "function", "function": {"name": "parse_dates"}}],
        )


@pytest.mark.asyncio
async def test_non_tool_flow_allowed_without_tool_support(monkeypatch):
    c = OllamaClient(supports_tools=False)

    async def fake_post(path, payload):
        assert "tools" not in payload
        return {"message": {"content": "hello there"}}

    monkeypatch.setattr(c, "_post", fake_post)
    resp = await c.chat_with_tools(messages=[{"role": "user", "content": "hi"}], tools=[])

    assert resp.stop_reason == "end_turn"
    assert any(getattr(b, "text", None) == "hello there" for b in resp.blocks)


@pytest.mark.asyncio
async def test_chat_json_parses_ollama_response(monkeypatch):
    c = OllamaClient()

    async def fake_post(path, payload):
        assert path == "/api/chat"
        assert payload["format"] == "json"
        return {"message": {"content": '{"intent": "draft_contract"}'}}

    monkeypatch.setattr(c, "_post", fake_post)
    out = await c.chat_json("classify this")
    assert out == {"intent": "draft_contract"}


@pytest.mark.asyncio
async def test_tool_capable_model_maps_tool_calls(monkeypatch):
    c = OllamaClient(model="llama3.1", supports_tools=True)

    async def fake_post(path, payload):
        assert payload["tools"]
        return {
            "message": {
                "content": "",
                "tool_calls": [
                    {"function": {"name": "parse_dates", "arguments": {"text": "tomorrow"}}}
                ],
            }
        }

    monkeypatch.setattr(c, "_post", fake_post)
    resp = await c.chat_with_tools(
        messages=[{"role": "user", "content": "when?"}],
        tools=[{"type": "function", "function": {"name": "parse_dates"}}],
    )
    assert resp.stop_reason == "tool_use"
    assert resp.blocks[0].name == "parse_dates"
    assert resp.blocks[0].input == {"text": "tomorrow"}
