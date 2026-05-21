import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from services.rag_system.rag_service import app

client = TestClient(app)

@pytest.fixture
def mock_rag_system():
    with patch('services.rag_system.rag_service.rag_system') as mock:
        yield mock

def test_rag_status():
    """Test health check endpoint."""
    response = client.get("/rag/status")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "rag-system"}

@pytest.mark.asyncio
async def test_rag_query_endpoint(mock_rag_system):
    """Test the main RAG query endpoint."""
    # Setup mock return
    mock_rag_system.query = AsyncMock(return_value={
        "answer": "Mocked answer [CITATION: 1]",
        "citations": ["1"],
        "validation": {"all_valid": True},
        "confidence_score": 0.95
    })
    
    payload = {"query": "test query", "collection": "uk_compliance"}
    response = client.post("/rag/query", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Mocked answer [CITATION: 1]"
    assert data["confidence_score"] == 0.95
    mock_rag_system.query.assert_called_once_with("test query", collection_name="uk_compliance")

def test_rag_query_validation_error():
    """Test with missing required fields."""
    response = client.post("/rag/query", json={}) # Missing 'query'
    assert response.status_code == 422

def test_rag_verify_endpoint(mock_rag_system):
    """Test citation verification endpoint."""
    mock_rag_system.citation_tracker.extract_citations.return_value = ["1"]
    mock_rag_system.citation_tracker.validate_citations.return_value = {"all_valid": True}
    
    payload = {
        "text": "test text [CITATION: 1]",
        "retrieved_docs": [{"id": "1"}]
    }
    response = client.post("/rag/verify", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["citations"] == ["1"]
    assert data["validation"]["all_valid"] is True

def test_rag_query_server_error(mock_rag_system):
    """Test server error handling."""
    mock_rag_system.query = AsyncMock(side_effect=Exception("Database down"))
    
    response = client.post("/rag/query", json={"query": "fail me"})
    assert response.status_code == 500
    assert "Database down" in response.json()["detail"]

import time

def test_rag_latency(mock_rag_system):
    """Ensure RAG endpoint response is under 200ms."""
    mock_rag_system.query = AsyncMock(return_value={
        "answer": "fast", "citations": [], "validation": {}, "confidence_score": 1.0
    })
    
    start = time.time()
    response = client.post("/rag/query", json={"query": "fast query"})
    elapsed = (time.time() - start) * 1000
    
    assert response.status_code == 200
    assert elapsed < 200
    print(f"RAG Latency: {elapsed:.2f}ms")
