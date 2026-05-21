import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from services.analyst_agent.analyst_service import app
from services.analyst_agent.confidence import compute_confidence

client = TestClient(app)

@pytest.fixture
def mock_agent():
    with patch('services.analyst_agent.analyst_service.analyst_agent') as mock:
        yield mock

def test_explanation_payload_structure():
    """Test the structure of the decision explanation response."""
    payload = {
        "query": "Is data encrypted?",
        "decision_id": "DEC-123"
    }
    response = client.post("/analyst/decision/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "matched_policies" in data
    assert "rejected_policies" in data
    assert "clause_rationale" in data
    assert len(data["clause_rationale"]) > 0
    assert data["clause_rationale"][0]["impact"] in ["Positive", "Negative"]
    assert "decision_path" in data
    assert "triggering_evidence" in data

def test_confidence_computation_bands():
    """Test confidence scoring logic and bands."""
    # Low band
    low = compute_confidence(0.1, 0.1, 0.1)
    assert low.band == "low"
    assert low.score < 0.4
    
    # Medium band
    med = compute_confidence(0.5, 0.6, 0.5)
    assert med.band == "medium"
    
    # High band
    high = compute_confidence(0.9, 0.9, 0.9)
    assert high.band == "high"
    assert high.score >= 0.7

@pytest.mark.asyncio
async def test_confidence_integration_in_analyze(mock_agent):
    """Test that /analyze returns confidence details."""
    mock_agent.analyze = AsyncMock(return_value={
        "analysis": "Test",
        "citations": [],
        "risk_assessment": {},
        "recommendations": [],
        "confidence": 0.8
    })
    
    response = client.post("/analyst/analyze", json={"query": "test"})
    assert response.status_code == 200
    data = response.json()
    assert "confidence_details" in data
    assert data["confidence_details"]["band"] in ["low", "medium", "high"]

def test_confidence_integration_in_evaluate():
    """Test that /approval/evaluate returns confidence details."""
    payload = {
        "request_type": "exception",
        "title": "Test Title",
        "description": "Providing details for high completeness",
        "requestor": "admin",
        "deadline": "2024-12-31",
        "approval_strategy": "any_can_approve"
    }
    response = client.post("/analyst/approval/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "confidence_details" in data
    assert data["confidence_details"]["factors"]["data_completeness"] == 0.95

def test_low_confidence_guardrail_logic():
    """Verify that low confidence scores are correctly identified."""
    # Logic: score < 0.4 is 'low'
    score = compute_confidence(0.2, 0.2, 0.2)
    assert score.band == "low"
    # Frontend will use this 'low' band to trigger explicit acknowledgement

def test_explanation_endpoint_bad_payload():
    """Test validation for explanation endpoint."""
    response = client.post("/analyst/decision/explain", json={"query": "missing decision_id"})
    assert response.status_code == 422

def test_clause_rationale_schema():
    """Test that rationale schema is respected."""
    response = client.post("/analyst/decision/explain", json={"query": "test", "decision_id": "1"})
    data = response.json()
    for rationale in data["clause_rationale"]:
        assert "clause_id" in rationale
        assert "reasoning" in rationale
        assert "impact" in rationale
