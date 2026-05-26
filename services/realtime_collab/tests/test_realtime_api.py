from __future__ import annotations

from fastapi.testclient import TestClient

from services.realtime_collab.main import app
from services.realtime_collab.manager import manager


def test_health_and_ready() -> None:
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "ok", "service": "realtime-collab"}
    assert client.get("/ready").json() == {"status": "ready"}


def test_rest_operation_and_snapshot() -> None:
    client = TestClient(app)

    response = client.post(
        "/collab/documents/rest-doc/operations",
        json={
            "operation_id": "op-1",
            "client_id": "alice",
            "base_version": 0,
            "operation": "replace",
            "text": "draft",
        },
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    snapshot = client.get("/collab/documents/rest-doc").json()
    assert snapshot["version"] == 1
    assert snapshot["content"] == "draft"


def test_websocket_receives_snapshot_and_operation_broadcast() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/collab/ws-doc?client_id=alice") as websocket:
        snapshot = websocket.receive_json()
        assert snapshot["type"] == "snapshot"
        assert snapshot["version"] == 0

        presence = websocket.receive_json()
        assert presence["type"] == "presence"
        assert presence["active_clients"] == ["alice"]

        websocket.send_json(
            {
                "operation_id": "op-1",
                "base_version": 0,
                "operation": "replace",
                "text": "live text",
            }
        )
        event = websocket.receive_json()
        assert event["type"] == "operation_applied"
        assert event["content"] == "live text"
        assert event["version"] == 1


def test_websocket_conflict_response_for_stale_operation() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/collab/conflict-doc?client_id=alice") as websocket:
        websocket.receive_json()
        websocket.receive_json()
        websocket.send_json(
            {
                "operation_id": "op-1",
                "base_version": 0,
                "operation": "replace",
                "text": "first",
            }
        )
        websocket.receive_json()
        websocket.send_json(
            {
                "operation_id": "op-2",
                "base_version": 0,
                "operation": "replace",
                "text": "stale",
            }
        )
        conflict = websocket.receive_json()
        assert conflict["type"] == "conflict"
        assert conflict["version"] == 1
        assert conflict["content"] == "first"


def teardown_module() -> None:
    import asyncio

    asyncio.run(manager.reset())
