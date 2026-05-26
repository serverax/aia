"""Unit tests for the Editor agent's pure transform (no Redis/Postgres).

Exercises `build_reply` directly and verifies the default Markdown renderer
plus an injected custom renderer, matching how `echo_agent` tests bind a
lightweight stub holding just `settings`.
"""

from __future__ import annotations

import base64

from libs.communication import AgentMessage, MessageStatus, MessageType
from services.editor_agent.main import EditorAgent, Settings, render_markdown


def _incoming() -> AgentMessage:
    return AgentMessage(
        from_agent="orchestrator",
        to_agent="editor-v1",
        task_id="task-123",
        message_type=MessageType.TASK_ASSIGNMENT,
        status=MessageStatus.IN_PROGRESS,
        data={
            "title": "Settlement Summary",
            "format": "md",
            "sections": {"executive_summary": "All clear.", "recommendations": "Proceed."},
        },
        metadata={"trace": "abc"},
    )


def test_render_markdown_includes_title_and_sections():
    body, mime = render_markdown(_incoming().data)
    text = body.decode("utf-8")
    assert mime == "text/markdown"
    assert "# Settlement Summary" in text
    assert "## Executive Summary" in text
    assert "Proceed." in text


def test_build_reply_wraps_artifact_and_completes():
    settings = Settings()
    # Bind build_reply without constructing real Redis/OTel clients.
    stub = type("Stub", (), {"settings": settings, "renderer": staticmethod(render_markdown)})()
    reply = EditorAgent.build_reply(stub, _incoming())  # type: ignore[arg-type]

    assert reply.message_type == MessageType.TASK_COMPLETE
    assert reply.status == MessageStatus.COMPLETED
    assert reply.to_agent == "orchestrator"
    assert reply.task_id == "task-123"
    assert reply.metadata["in_reply_to"] == _incoming().message_id or "in_reply_to" in reply.metadata

    decoded = base64.b64decode(reply.data["artifact_b64"])
    assert b"# Settlement Summary" in decoded
    assert reply.data["byte_length"] == len(decoded)


def test_injected_renderer_is_used():
    def fake_renderer(payload):
        return b"PDFBYTES", "application/pdf"

    settings = Settings()
    stub = type("Stub", (), {"settings": settings, "renderer": staticmethod(fake_renderer)})()
    reply = EditorAgent.build_reply(stub, _incoming())  # type: ignore[arg-type]

    assert reply.data["mime_type"] == "application/pdf"
    assert base64.b64decode(reply.data["artifact_b64"]) == b"PDFBYTES"
