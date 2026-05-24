from fastapi.testclient import TestClient

from services.editor_agent.api.main import app

client = TestClient(app)


def test_health_route():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_templates_route():
    response = client.get("/api/v1/templates")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 5
