from __future__ import annotations


def test_root_metadata(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["docs"] == "/docs"


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_readyz_ready_with_fake_db(client):
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_openapi_lists_scoring_route(client):
    spec = client.get("/openapi.json").json()
    assert "/applications/{row_id}/score" in spec["paths"]
