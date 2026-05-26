from __future__ import annotations

import pytest

from services.realtime_collab.manager import CollaborationManager
from services.realtime_collab.models import CollaborationOperation


@pytest.mark.asyncio
async def test_replace_operation_creates_versioned_snapshot() -> None:
    manager = CollaborationManager()
    result = await manager.apply_operation(
        "doc-1",
        CollaborationOperation(
            operation_id="op-1",
            client_id="alice",
            base_version=0,
            operation="replace",
            text="hello",
        ),
    )

    assert result.accepted is True
    assert result.snapshot.version == 1
    assert result.snapshot.content == "hello"
    assert result.event.type == "operation_applied"


@pytest.mark.asyncio
async def test_insert_and_delete_are_deterministic() -> None:
    manager = CollaborationManager()
    await manager.apply_operation(
        "doc-1",
        CollaborationOperation(
            operation_id="op-1",
            client_id="alice",
            base_version=0,
            operation="replace",
            text="hello",
        ),
    )
    inserted = await manager.apply_operation(
        "doc-1",
        CollaborationOperation(
            operation_id="op-2",
            client_id="bob",
            base_version=1,
            operation="insert",
            position=5,
            text=" world",
        ),
    )
    deleted = await manager.apply_operation(
        "doc-1",
        CollaborationOperation(
            operation_id="op-3",
            client_id="alice",
            base_version=2,
            operation="delete",
            position=5,
            length=1,
        ),
    )

    assert inserted.snapshot.content == "hello world"
    assert deleted.snapshot.version == 3
    assert deleted.snapshot.content == "helloworld"


@pytest.mark.asyncio
async def test_stale_base_version_returns_conflict_without_mutating_document() -> None:
    manager = CollaborationManager()
    await manager.apply_operation(
        "doc-1",
        CollaborationOperation(
            operation_id="op-1",
            client_id="alice",
            base_version=0,
            operation="replace",
            text="current",
        ),
    )
    result = await manager.apply_operation(
        "doc-1",
        CollaborationOperation(
            operation_id="op-stale",
            client_id="bob",
            base_version=0,
            operation="replace",
            text="stale",
        ),
    )

    assert result.accepted is False
    assert result.event.type == "conflict"
    assert "stale base_version" in (result.event.message or "")
    assert result.snapshot.version == 1
    assert result.snapshot.content == "current"


@pytest.mark.asyncio
async def test_invalid_delete_range_returns_error() -> None:
    manager = CollaborationManager()
    await manager.apply_operation(
        "doc-1",
        CollaborationOperation(
            operation_id="op-1",
            client_id="alice",
            base_version=0,
            operation="replace",
            text="abc",
        ),
    )
    result = await manager.apply_operation(
        "doc-1",
        CollaborationOperation(
            operation_id="op-bad",
            client_id="alice",
            base_version=1,
            operation="delete",
            position=2,
            length=5,
        ),
    )

    assert result.accepted is False
    assert result.event.type == "error"
    assert result.snapshot.content == "abc"
