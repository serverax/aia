"""Test fixtures for the Hiring API.

The client is built **without** the lifespan context manager so startup never
tries to reach a real Postgres. We inject a :class:`FakeDatabase` and a real
:class:`HeuristicScorer` (deterministic, no API key) onto ``app.state`` and via
dependency overrides, so the whole suite runs hermetically.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.db import FakeDatabase
from apps.api.deps import get_db, get_scorer
from apps.api.main import create_app
from apps.api.scoring import HeuristicScorer


@pytest.fixture
def fake_db() -> FakeDatabase:
    return FakeDatabase()


@pytest.fixture
def client(fake_db: FakeDatabase) -> TestClient:
    app = create_app()
    scorer = HeuristicScorer()
    # Set on state for the health probes, and override deps for the routers.
    app.state.db = fake_db
    app.state.scorer = scorer
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_scorer] = lambda: scorer
    return TestClient(app)
