"""Auth enforcement on the Hiring API CRUD routes.

Builds the app WITHOUT overriding the auth dependency (unlike conftest.client),
so it exercises real JWT validation via libs.auth. DB/scorer are still faked so
the suite stays hermetic.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.db import FakeDatabase
from apps.api.deps import get_db, get_scorer
from apps.api.main import create_app
from apps.api.scoring import HeuristicScorer
from libs.auth import create_access_token

pytestmark = [pytest.mark.unit]


def _client() -> TestClient:
    app = create_app()
    db = FakeDatabase()
    app.state.db = db
    app.state.scorer = HeuristicScorer()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_scorer] = lambda: HeuristicScorer()
    return TestClient(app)


def _bearer(scopes):
    return {"Authorization": "Bearer " + create_access_token({"sub": "u", "scopes": scopes})}


def test_health_is_public():
    assert _client().get("/healthz").status_code == 200


def test_crud_rejects_anonymous():
    resp = _client().post("/companies", json={"name": "Acme Ltd"})
    assert resp.status_code == 401


def test_crud_rejects_token_without_items_scope():
    resp = _client().post("/companies", headers=_bearer(["me"]), json={"name": "Acme Ltd"})
    assert resp.status_code == 403


def test_crud_allows_authenticated_user():
    resp = _client().post("/companies", headers=_bearer(["items"]), json={"name": "Acme Ltd"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Acme Ltd"


def test_list_also_requires_auth():
    assert _client().get("/companies").status_code == 401
