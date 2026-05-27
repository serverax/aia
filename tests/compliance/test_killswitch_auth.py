"""Auth tests for the compliance kill-switch.

Proves that mutating the global kill-switch requires an authenticated admin —
previously any anonymous caller could halt every agent (audit finding F-2).
Tokens are minted with the shared libs.auth secret; no live service needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[2] / "services" / "compliance-service"
sys.path.insert(0, str(SERVICE_ROOT))

from compliance_service.main import app  # noqa: E402

from libs.auth import create_access_token  # noqa: E402

pytestmark = [pytest.mark.unit]

_BODY = {"global_enabled": True, "reason": "test", "updated_by": "tester"}


def _bearer(scopes):
    return {"Authorization": "Bearer " + create_access_token({"sub": "t", "scopes": scopes})}


def test_put_killswitch_rejects_anonymous():
    client = TestClient(app)
    resp = client.put("/compliance/kill-switch", json=_BODY)
    assert resp.status_code == 401


def test_put_killswitch_rejects_non_admin_scope():
    client = TestClient(app)
    resp = client.put("/compliance/kill-switch", headers=_bearer(["items"]), json=_BODY)
    assert resp.status_code == 403


def test_put_killswitch_allows_admin():
    client = TestClient(app)
    resp = client.put(
        "/compliance/kill-switch",
        headers=_bearer(["admin"]),
        json={"global_enabled": False, "reason": "reset", "updated_by": "admin"},
    )
    assert resp.status_code == 200


def test_evaluate_stays_open_for_orchestrator_gate():
    # The orchestrator admission gate calls /evaluate without a user token.
    client = TestClient(app)
    resp = client.post("/compliance/evaluate", json={"agent_id": "analyst-v1"})
    assert resp.status_code == 200
