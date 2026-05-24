"""Shared pytest fixtures.

Integration tests assume the dev stack from
`infrastructure/docker-compose.dev.yml` is already up:

    docker compose -f infrastructure/docker-compose.dev.yml up -d \
        postgres redis jaeger

The echo-agent service itself can be running there too, OR you can run it
locally with `uvicorn services.echo_agent.main:app` against the same
Postgres/Redis. Tests don't care which.
"""

from __future__ import annotations

import os
import socket

import pytest


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session")
def redis_host() -> str:
    return os.environ.get("REDIS_HOST", "localhost")


@pytest.fixture(scope="session")
def postgres_host() -> str:
    return os.environ.get("POSTGRES_HOST", "localhost")


@pytest.fixture(scope="session", autouse=False)
def require_dev_stack(redis_host: str, postgres_host: str) -> None:
    """Skip integration tests if the dev stack isn't reachable."""
    missing = []
    if not _port_open(redis_host, int(os.environ.get("REDIS_PORT", "6379"))):
        missing.append(f"redis @ {redis_host}:6379")
    if not _port_open(postgres_host, int(os.environ.get("POSTGRES_PORT", "5432"))):
        missing.append(f"postgres @ {postgres_host}:5432")
    if missing:
        pytest.skip(
            "dev stack not reachable: "
            + ", ".join(missing)
            + " (run `docker compose -f infrastructure/docker-compose.dev.yml up -d`)"
        )
