"""Unit tests for Echo Agent message construction.

Loop-level behavior (Redis Streams + Postgres + OTLP) is covered by the
integration tests in `tests/integration/`. Here we only assert the pure
transformation: incoming message -> echoed reply.
"""

from __future__ import annotations

import pytest

from libs.communication import AgentMessage, MessageStatus, MessageType
from services.echo_agent.main import EchoAgent, Settings


@pytest.mark.unit
def test_build_echo_swaps_from_and_to():
    settings = Settings(agent_id="echo-test")
    incoming = AgentMessage(
        from_agent="orchestrator",
        to_agent="echo-test",
        task_id="task-42",
        message_type=MessageType.ECHO,
        status=MessageStatus.PENDING,
        data={"payload": "hi"},
    )

    # _build_echo is a pure method; bind via a stub holding just `settings`
    # so we don't need Redis/Postgres connections.
    stub = type("Stub", (), {"settings": settings})()
    reply = EchoAgent._build_echo(stub, incoming)  # type: ignore[arg-type]

    assert reply.from_agent == "echo-test"
    assert reply.to_agent == "orchestrator"
    assert reply.task_id == "task-42"
    assert reply.message_type is MessageType.ECHO
    assert reply.status is MessageStatus.COMPLETED
    assert reply.data["echoed"] == {"payload": "hi"}
    assert reply.metadata["in_reply_to"] == incoming.message_id
