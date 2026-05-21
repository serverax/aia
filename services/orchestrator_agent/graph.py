"""LangGraph wiring.

`build_graph()` returns a compiled graph. Construction is parameterized so
tests can inject a StubLLMClient and a fakeredis client without monkey-patching
imports.
"""
from __future__ import annotations

from typing import Any

import asyncpg
import redis.asyncio as aioredis
from langgraph.graph import END, StateGraph

from libs.llm import LLMClient
from services.orchestrator_agent.conflict import make_conflict_resolver
from services.orchestrator_agent.monitor import make_monitor
from services.orchestrator_agent.nodes import (
    conflict_branch,
    make_intent_parser,
    make_task_decomposer,
    should_continue,
)
from services.orchestrator_agent.router import make_router
from services.orchestrator_agent.state import OrchestratorState


async def _clarification_terminal(state: OrchestratorState) -> dict[str, Any]:
    """Terminal node when the LLM requested clarification."""
    return {"current_phase": "awaiting_clarification"}


async def _completion_terminal(state: OrchestratorState) -> dict[str, Any]:
    return {"current_phase": "done"}


def build_graph(
    *,
    llm: LLMClient,
    redis_client: aioredis.Redis,
    pg_pool: asyncpg.Pool | None = None,
    max_concurrent_dispatches: int = 20,
    monitor_timeout_seconds: float = 60.0,
):
    """Wire all nodes into a StateGraph and compile it."""
    graph = StateGraph(OrchestratorState)

    graph.add_node("intent_parser", make_intent_parser(llm))
    graph.add_node("task_decomposer", make_task_decomposer(llm))
    graph.add_node("router", make_router(redis_client, max_concurrent=max_concurrent_dispatches))
    graph.add_node("monitor", make_monitor(redis_client, timeout_seconds=monitor_timeout_seconds))
    graph.add_node("conflict_resolver", make_conflict_resolver(redis_client, pg_pool))
    graph.add_node("clarify", _clarification_terminal)
    graph.add_node("complete", _completion_terminal)

    graph.set_entry_point("intent_parser")
    graph.add_conditional_edges(
        "intent_parser",
        should_continue,
        {"clarify": "clarify", "decompose": "task_decomposer"},
    )
    graph.add_edge("task_decomposer", "router")
    graph.add_edge("router", "monitor")
    graph.add_edge("monitor", "conflict_resolver")
    graph.add_conditional_edges(
        "conflict_resolver",
        conflict_branch,
        {"escalate": END, "complete": "complete"},
    )
    graph.add_edge("clarify", END)
    graph.add_edge("complete", END)

    return graph.compile()
