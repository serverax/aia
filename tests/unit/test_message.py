"""Unit tests for the typed AgentMessage envelope."""

from __future__ import annotations

import json

import pytest

from libs.communication import AgentMessage, MessageStatus, MessageType


@pytest.mark.unit
def test_round_trip_through_stream_fields():
    original = AgentMessage(
        from_agent="orchestrator",
        to_agent="echo",
        task_id="t1",
        message_type=MessageType.ECHO,
        status=MessageStatus.PENDING,
        data={"hello": "world", "count": 3},
        metadata={"trace_id": "abc"},
    )
    fields = original.to_stream_fields()

    # All fields must be flat strings for Redis Streams.
    for key, value in fields.items():
        assert isinstance(value, str), f"{key} is {type(value)}, expected str"

    rebuilt = AgentMessage.from_stream_fields(fields)
    assert rebuilt.message_id == original.message_id
    assert rebuilt.from_agent == original.from_agent
    assert rebuilt.to_agent == original.to_agent
    assert rebuilt.task_id == original.task_id
    assert rebuilt.message_type is MessageType.ECHO
    assert rebuilt.status is MessageStatus.PENDING
    assert rebuilt.data == original.data
    assert rebuilt.metadata == original.metadata


@pytest.mark.unit
def test_from_stream_fields_tolerates_missing_optional_fields():
    minimal = {
        "from_agent": "a",
        "to_agent": "b",
        "task_id": "t",
        "message_type": "echo",
        "status": "pending",
    }
    msg = AgentMessage.from_stream_fields(minimal)
    assert msg.data == {}
    assert msg.metadata == {}
    assert msg.message_id  # auto-assigned
    assert msg.timestamp


@pytest.mark.unit
def test_data_json_encoded_on_wire():
    msg = AgentMessage(
        from_agent="a",
        to_agent="b",
        task_id="t",
        message_type=MessageType.ECHO,
        status=MessageStatus.COMPLETED,
        data={"nested": [1, 2, 3]},
    )
    fields = msg.to_stream_fields()
    decoded = json.loads(fields["data"])
    assert decoded == {"nested": [1, 2, 3]}
