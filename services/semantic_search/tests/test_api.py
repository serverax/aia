import pytest
from fastapi.testclient import TestClient

from services.semantic_search.api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["document_count"] >= 50  # Should have sample data


def test_search_api():
    response = client.post("/search", json={"query": "GDPR data privacy", "top_k": 3})
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0
    assert "GDPR" in results[0]["content"]


def test_search_with_filters():
    response = client.post(
        "/search", json={"query": "compliance policy", "filters": {"jurisdiction": "UK"}}
    )
    assert response.status_code == 200
    results = response.json()
    for res in results:
        assert res["jurisdiction"] == "UK"


def test_embed_api():
    response = client.post("/embed", json={"texts": ["hello", "world"]})
    assert response.status_code == 200
    data = response.json()
    assert len(data["embeddings"]) == 2
    assert len(data["embeddings"][0]) == 384
