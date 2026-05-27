"""Production guard: dev-only auth must not run in production.

`assert_auth_safe_for_production()` raises when AIA_ENV is production and the
service is still on the in-memory fake_users_db / dev-default JWT secret, unless
AIA_ALLOW_DEV_AUTH is explicitly set.
"""

from __future__ import annotations

import pytest

import libs.auth.security as sec
from libs.auth import assert_auth_safe_for_production

pytestmark = [pytest.mark.unit]


def test_dev_env_is_allowed(monkeypatch):
    monkeypatch.delenv("AIA_ENV", raising=False)
    assert_auth_safe_for_production()  # no raise in dev


def test_non_prod_env_is_allowed(monkeypatch):
    monkeypatch.setenv("AIA_ENV", "staging")
    assert_auth_safe_for_production()  # only prod/production are guarded


def test_production_with_fake_auth_refuses(monkeypatch):
    monkeypatch.setenv("AIA_ENV", "production")
    monkeypatch.delenv("AIA_ALLOW_DEV_AUTH", raising=False)
    with pytest.raises(RuntimeError, match="Refusing dev-only auth"):
        assert_auth_safe_for_production()


def test_explicit_override_allows(monkeypatch):
    monkeypatch.setenv("AIA_ENV", "prod")
    monkeypatch.setenv("AIA_ALLOW_DEV_AUTH", "true")
    assert_auth_safe_for_production()  # explicit override


def test_real_secret_but_fake_userdb_still_refuses(monkeypatch):
    # Even with a strong secret, the in-memory user store is a prod blocker.
    monkeypatch.setenv("AIA_ENV", "production")
    monkeypatch.delenv("AIA_ALLOW_DEV_AUTH", raising=False)
    monkeypatch.setattr(sec, "SECRET_KEY", "a-real-and-strong-secret-value", raising=False)
    with pytest.raises(RuntimeError, match="fake_users_db"):
        assert_auth_safe_for_production()
