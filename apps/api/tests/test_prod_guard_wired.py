"""R-2: production guard must be wired into the Hiring API lifespan.

Mirrors the orchestrator's pattern (services/orchestrator_agent/main.py): if
AIA_ENV is production and the service is still on the in-memory fake_users_db
or the dev-default JWT secret, startup must raise instead of accepting forged
JWTs against the public CRUD surface.

These tests intentionally do NOT use conftest.client (which overrides
get_current_active_user) — they exercise the real lifespan via TestClient's
context manager.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app

pytestmark = [pytest.mark.unit]


def test_lifespan_refuses_dev_auth_in_production(monkeypatch):
    monkeypatch.setenv("AIA_ENV", "production")
    monkeypatch.delenv("AIA_ALLOW_DEV_AUTH", raising=False)
    app = create_app()
    with pytest.raises(RuntimeError, match="Refusing dev-only auth"):
        with TestClient(app):
            pass


def test_lifespan_allows_dev_environment(monkeypatch):
    monkeypatch.delenv("AIA_ENV", raising=False)
    monkeypatch.delenv("AIA_ALLOW_DEV_AUTH", raising=False)
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200


def test_lifespan_allows_explicit_override_in_production(monkeypatch):
    # Mirrors the orchestrator's escape hatch: an explicit override lets a
    # controlled staging smoke test run with the dev userdb intact.
    monkeypatch.setenv("AIA_ENV", "production")
    monkeypatch.setenv("AIA_ALLOW_DEV_AUTH", "true")
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
