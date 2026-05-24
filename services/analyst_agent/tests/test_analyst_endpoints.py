import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from services.analyst_agent.analyst_service import app

client = TestClient(app)


@pytest.fixture
def mock_agent():
    with patch("services.analyst_agent.analyst_service.analyst_agent") as mock:
        yield mock


@pytest.fixture
def mock_risk_analyzer():
    with patch("services.analyst_agent.analyst_service.risk_analyzer") as mock:
        yield mock


def test_analyst_status():
    """Test health check endpoint."""
    response = client.get("/analyst/status")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "analyst-agent"}


@pytest.mark.asyncio
async def test_analyst_analyze_endpoint(mock_agent):
    """Test the full analysis endpoint."""
    mock_agent.analyze = AsyncMock(
        return_value={
            "analysis": "Detailed analysis",
            "citations": ["doc_1"],
            "risk_assessment": {"overall_level": "LOW"},
            "recommendations": [],
            "confidence": 0.85,
        }
    )

    payload = {"query": "Analyze this", "context": "Optional context"}
    response = client.post("/analyst/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["analysis"] == "Detailed analysis"
    assert data["confidence"] == 0.85
    mock_agent.analyze.assert_called_once_with("Analyze this", "Optional context")


def test_analyst_risks_only_endpoint(mock_risk_analyzer):
    """Test the risks-only endpoint."""
    mock_risk_analyzer.assess.return_value = {"overall_level": "HIGH"}

    payload = {"text": "risk keywords", "citations": ["doc_1"]}
    response = client.post("/analyst/risks-only", json=payload)

    assert response.status_code == 200
    assert response.json()["risk_assessment"] == {"overall_level": "HIGH"}
    mock_risk_analyzer.assess.assert_called_once_with("risk keywords", ["doc_1"])


def test_analyst_analyze_server_error(mock_agent):
    """Test server error handling."""
    mock_agent.analyze = AsyncMock(side_effect=RuntimeError("LLM Timeout"))

    response = client.post("/analyst/analyze", json={"query": "timeout query"})
    assert response.status_code == 500
    assert "LLM Timeout" in response.json()["detail"]


def test_approval_evaluate_success():
    payload = {
        "request_type": "exception",
        "title": "Vendor Encryption Exception",
        "description": "Temporary exception pending migration.",
        "requestor": "analyst@synthetic.io",
        "deadline": "2026-05-25T17:00:00Z",
        "approval_strategy": "all_must_approve",
        "metadata": {"risk_score": 8.4},
    }
    response = client.post("/analyst/approval/evaluate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["risk_score"] == 8.4
    assert "security_lead@synthetic.io" in body["recommended_reviewers"]


def test_approval_evaluate_bad_request_type():
    payload = {
        "request_type": "unsupported",
        "title": "Invalid Request",
        "description": "desc",
        "requestor": "analyst@synthetic.io",
        "deadline": "2026-05-25T17:00:00Z",
        "approval_strategy": "all_must_approve",
        "metadata": {"risk_score": 4.1},
    }
    response = client.post("/analyst/approval/evaluate", json=payload)
    assert response.status_code == 400
    assert "Unsupported request_type" in response.json()["detail"]


import time


def test_analyst_latency(mock_agent):
    """Ensure endpoint response is under 200ms."""
    mock_agent.analyze = AsyncMock(
        return_value={
            "analysis": "fast",
            "citations": ["doc_1"],
            "risk_assessment": {"overall_level": "LOW"},
            "recommendations": [],
            "confidence": 0.92,
        }
    )

    start = time.time()
    response = client.post("/analyst/analyze", json={"query": "fast query"})
    elapsed = (time.time() - start) * 1000

    assert response.status_code == 200
    assert elapsed < 200
    print(f"Analyst Latency: {elapsed:.2f}ms")
