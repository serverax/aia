"""Unit tests for the original libs/communication/protocol.py helper."""
from __future__ import annotations

import uuid

import pytest

from libs.communication.protocol import create_message


@pytest.mark.unit
def test_create_message_required_fields():
    msg = create_message(
        from_agent="orchestrator",
        to_agent="echo",
        task_id="t1",
        message_type="echo",
        status="pending",
    )
    assert msg["from_agent"] == "orchestrator"
    assert msg["to_agent"] == "echo"
    assert msg["task_id"] == "t1"
    assert msg["message_type"] == "echo"
    assert msg["status"] == "pending"
    assert msg["data"] == {}
    assert msg["metadata"] == {}


@pytest.mark.unit
def test_create_message_assigns_unique_id():
    a = create_message("o", "e", "t", "echo", "pending")
    b = create_message("o", "e", "t", "echo", "pending")
    assert a["message_id"] != b["message_id"]
    # Sanity-check it's a UUID string.
    uuid.UUID(a["message_id"])


@pytest.mark.unit
def test_create_message_timestamp_is_utc_iso():
    msg = create_message("o", "e", "t", "echo", "pending")
    assert msg["timestamp"].endswith("Z")


@pytest.mark.unit
def test_create_message_carries_data_payload():
    payload = {"hello": "world", "nested": {"a": 1}}
    msg = create_message("o", "e", "t", "echo", "pending", data=payload)
    assert msg["data"] == payload
