"""Claude tool-use protocol on top of LLMClient.

The Anthropic Messages API lets a model return `tool_use` content blocks
asking the host to run a named tool with a structured input. The host
runs the tool (in our case via `services.tool_sandbox.ToolRegistry`),
sends the result back as a `tool_result` block, and the loop continues
until the model returns plain text only.

This module is the glue between `LLMClient` and `ToolRegistry`. Agents
that want tool-use call `agent_loop(...)`; nothing else changes for them.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol

logger = logging.getLogger(__name__)


# ---- Anthropic message shapes -----------------------------------------
# We model just the bits the loop needs. The actual Anthropic SDK types
# carry more fields; agents that need them can build full messages
# themselves and call the LLMClient directly.

@dataclass
class TextBlock:
    text: str
    type: str = "text"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "text", "text": self.text}


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "tool_use", "id": self.id, "name": self.name, "input": self.input}


@dataclass
class ToolResultBlock:
    tool_use_id: str
    content: str          # JSON-encoded tool output (or error message)
    is_error: bool = False
    type: str = "tool_result"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": self.tool_use_id,
            "content": self.content,
            "is_error": self.is_error,
        }


@dataclass
class AssistantResponse:
    """One turn of model output.

    `stop_reason` of `tool_use` means the host must run tools and reply.
    Anything else (`end_turn`, `stop_sequence`, `max_tokens`) terminates
    the loop.
    """

    blocks: list[TextBlock | ToolUseBlock]
    stop_reason: str

    @property
    def tool_uses(self) -> list[ToolUseBlock]:
        return [b for b in self.blocks if isinstance(b, ToolUseBlock)]

    @property
    def text(self) -> str:
        return "".join(b.text for b in self.blocks if isinstance(b, TextBlock))


# ---- LLMClient extension --------------------------------------------------

class ToolCapableLLMClient(Protocol):
    """`LLMClient` extended with the tool-use entry point.

    Real implementation in `libs.llm.client.AnthropicClient.chat_with_tools`.
    Stub for tests in `libs.llm.client.StubLLMClient.chat_with_tools`.
    """

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> AssistantResponse:
        ...


# ---- ToolRegistry → Anthropic spec ---------------------------------------

# Anyone with a `ToolDescriptor` (from services.tool_sandbox.registry) can use
# this. We don't import ToolDescriptor here to keep this module dependency-light;
# instead we duck-type on the attributes the converter needs.

class _DescriptorLike(Protocol):
    name: str
    description: str
    input_schema: dict[str, Any]


def to_anthropic_spec(descriptor: _DescriptorLike) -> dict[str, Any]:
    """Convert a ToolDescriptor to the format Claude's API expects.

    See https://docs.anthropic.com/en/docs/build-with-claude/tool-use
    """
    return {
        "name": descriptor.name,
        "description": descriptor.description,
        "input_schema": descriptor.input_schema,
    }


# ---- The loop -------------------------------------------------------------

# A tool executor is anything that can run a tool by name for an agent.
# `ToolRegistry.execute` matches this signature exactly.
ToolExecutor = Callable[[str, str, dict[str, Any]], Awaitable[dict[str, Any]]]


async def agent_loop(
    *,
    llm: ToolCapableLLMClient,
    agent_id: str,
    initial_messages: list[dict[str, Any]],
    tool_descriptors: list[_DescriptorLike],
    tool_executor: ToolExecutor,
    system: str | None = None,
    max_iterations: int = 8,
) -> AssistantResponse:
    """Run a Claude tool-use conversation until it terminates.

    Args:
        llm: The tool-capable LLM client (Anthropic or stub).
        agent_id: Identifier passed to the tool executor for ACL + audit.
        initial_messages: Starting Anthropic messages (usually one user message).
        tool_descriptors: Tools the LLM is allowed to call this turn.
        tool_executor: Async callable `(agent_id, tool_name, input) -> output_dict`.
            In production this is `ToolRegistry.execute`.
        system: Optional system prompt.
        max_iterations: Safety cap on how many tool-use round-trips to allow.
            Beyond this we surface whatever the model said last + an error log.

    Returns:
        The model's final AssistantResponse (stop_reason != "tool_use").
    """
    import json

    tools_spec = [to_anthropic_spec(t) for t in tool_descriptors]
    messages: list[dict[str, Any]] = list(initial_messages)

    for iteration in range(max_iterations):
        response = await llm.chat_with_tools(
            messages=messages,
            tools=tools_spec,
            system=system,
        )

        # Always record the assistant turn — even pure-text — so the next
        # iteration has the right history.
        messages.append({
            "role": "assistant",
            "content": [b.to_dict() for b in response.blocks],
        })

        if response.stop_reason != "tool_use":
            return response

        # Run every tool_use in this turn, then send all results back in
        # ONE user message (Anthropic protocol expects that).
        result_blocks: list[ToolResultBlock] = []
        for tool_use in response.tool_uses:
            try:
                output = await tool_executor(agent_id, tool_use.name, tool_use.input)
                result_blocks.append(
                    ToolResultBlock(
                        tool_use_id=tool_use.id,
                        content=json.dumps(output, ensure_ascii=False),
                        is_error=False,
                    )
                )
            except Exception as exc:
                logger.warning(
                    "Tool %s failed for agent %s: %s",
                    tool_use.name, agent_id, exc,
                )
                result_blocks.append(
                    ToolResultBlock(
                        tool_use_id=tool_use.id,
                        content=json.dumps({"error": str(exc)}),
                        is_error=True,
                    )
                )

        messages.append({
            "role": "user",
            "content": [b.to_dict() for b in result_blocks],
        })

    logger.error(
        "agent_loop exceeded max_iterations=%d for agent %s",
        max_iterations, agent_id,
    )
    return response
