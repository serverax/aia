import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from services.analyst_agent.analyst_service import app
from uuid import UUID

client = TestClient(app)


@pytest.fixture
def mock_agent():
    with patch("services.analyst_agent.analyst_service.analyst_agent") as mock:
        yield mock


def test_document_lifecycle():
    """Test full document lifecycle: analyze -> preview -> finalize -> audit."""
    # 1. Analyze (Auto-creates draft)
    # Mocking analyst_agent.analyze to return a valid result
    with patch(
        "services.analyst_agent.analyst_service.analyst_agent.analyze", new_callable=AsyncMock
    ) as mock_analyze:
        mock_analyze.return_value = {
            "analysis": "This is a compliance report about encryption.",
            "citations": ["POL_001"],
            "risk_assessment": {"overall_level": "LOW"},
            "recommendations": [],
            "confidence": 0.9,
        }

        project_id = "ENCRYPT-10"
        response = client.post("/analyst/analyze", json={"query": project_id})
        assert response.status_code == 200

    # 2. Preview
    preview_resp = client.get(f"/analyst/document/preview?project_id={project_id}")
    assert preview_resp.status_code == 200
    assert "compliance report" in preview_resp.json()["html"]

    # 3. Finalize
    finalize_payload = {"project_id": project_id, "format": "PDF"}
    finalize_resp = client.post("/analyst/document/finalize", json=finalize_payload)
    assert finalize_resp.status_code == 201 or finalize_resp.status_code == 200
    doc_id = finalize_resp.json()["document_id"]
    assert finalize_resp.json()["file_url"].endswith(".pdf")

    # 4. Audit
    audit_resp = client.get(f"/analyst/document/audit/{doc_id}")
    assert audit_resp.status_code == 200
    history = audit_resp.json()
    assert len(history) >= 1
    assert history[0]["project_id"] == project_id
    assert history[0]["version"] == 1


def test_versioning():
    """Test that multiple analyses for the same project increment version."""
    project_id = "VERSION-01"

    with patch(
        "services.analyst_agent.analyst_service.analyst_agent.analyze", new_callable=AsyncMock
    ) as mock_analyze:
        mock_analyze.return_value = {
            "analysis": "v1",
            "citations": [],
            "risk_assessment": {},
            "recommendations": [],
            "confidence": 0.8,
        }
        client.post("/analyst/analyze", json={"query": project_id})

        mock_analyze.return_value = {
            "analysis": "v2",
            "citations": [],
            "risk_assessment": {},
            "recommendations": [],
            "confidence": 0.8,
        }
        client.post("/analyst/analyze", json={"query": project_id})

    # Check preview for version 2
    preview_resp = client.get(f"/analyst/document/preview?project_id={project_id}")
    assert preview_resp.json()["version"] == "latest"
    assert "v2" in preview_resp.json()["html"]

    v1_resp = client.get(f"/analyst/document/preview?project_id={project_id}&version=1")
    assert "v1" in v1_resp.json()["html"]


def test_finalize_invalid_project():
    """Test error handling for non-existent project."""
    response = client.post("/analyst/document/finalize", json={"project_id": "NON-EXISTENT"})
    assert response.status_code == 400
    assert "No drafts found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_bulk_export_workflow():
    """Test async bulk export triggering and status tracking."""
    payload = {"project_filters": {"jurisdiction": "EU"}, "format": "JSON"}
    # 1. Trigger
    trigger_resp = client.post("/analyst/export/bulk", json=payload)
    assert trigger_resp.status_code == 200
    job_id = trigger_resp.json()["job_id"]
    status_url = trigger_resp.json()["status_url"]

    # 2. Check initial status
    status_resp = client.get(status_url)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] in ["queued", "processing", "completed"]

    # 3. Wait for completion (simulated sleep in app is 5s)
    # In a real test, we might mock the sleep or wait.
    # For this verification, we'll wait a bit.
    import time

    time.sleep(6)

    final_status_resp = client.get(status_url)
    assert final_status_resp.json()["status"] == "completed"
    assert "download_url" in final_status_resp.json()
