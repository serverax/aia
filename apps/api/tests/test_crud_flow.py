"""End-to-end CRUD + scoring flow against the FakeDatabase."""

from __future__ import annotations


def test_company_lifecycle(client, fake_db):
    # create
    r = client.post("/companies", json={"name": "Acme Ltd", "country": "GB"})
    assert r.status_code == 201, r.text
    company = r.json()
    cid = company["id"]
    assert company["status"] == "active"  # default applied

    # get
    assert client.get(f"/companies/{cid}").status_code == 200

    # list
    listed = client.get("/companies").json()
    assert any(c["id"] == cid for c in listed)

    # patch
    r = client.patch(f"/companies/{cid}", json={"status": "archived"})
    assert r.status_code == 200
    assert r.json()["status"] == "archived"

    # delete + 404 afterwards
    assert client.delete(f"/companies/{cid}").status_code == 204
    assert client.get(f"/companies/{cid}").status_code == 404

    # every mutation was audited (create, update, delete)
    actions = [a["action"] for a in fake_db.audits if a["entity_type"] == "companies"]
    assert actions == ["create", "update", "delete"]


def test_unknown_id_is_404(client):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/jobs/{missing}").status_code == 404
    assert client.patch(f"/jobs/{missing}", json={"status": "open"}).status_code == 404
    assert client.delete(f"/jobs/{missing}").status_code == 404


def test_required_fields_and_email_validation(client):
    # job without required description -> 422
    assert client.post("/jobs", json={"title": "Engineer"}).status_code == 422
    # bad email -> 422
    assert client.post("/waitlist", json={"email": "not-an-email"}).status_code == 422
    # good email -> 201
    assert client.post("/waitlist", json={"email": "lead@example.com"}).status_code == 201


def test_list_filtering(client):
    client.post("/jobs", json={"title": "A", "description": "x", "status": "open"})
    client.post("/jobs", json={"title": "B", "description": "y", "status": "draft"})
    open_jobs = client.get("/jobs", params={"status": "open"}).json()
    assert len(open_jobs) == 1
    assert open_jobs[0]["title"] == "A"


def test_application_scoring_flow(client):
    job = client.post(
        "/jobs",
        json={
            "title": "Senior Python Engineer",
            "description": "Build async python services with fastapi and postgres.",
            "requirements": "python fastapi postgres async kubernetes",
        },
    ).json()
    candidate = client.post(
        "/candidates", json={"full_name": "Jane Doe", "email": "jane@example.com"}
    ).json()
    application = client.post(
        "/applications",
        json={
            "job_id": job["id"],
            "candidate_id": candidate["id"],
            "cover_letter": "Experienced python fastapi postgres async kubernetes engineer.",
            "cv_file_url": "https://cv.example/jane.pdf",
        },
    ).json()

    r = client.post(f"/applications/{application['id']}/score")
    assert r.status_code == 200, r.text
    scored = r.json()
    assert 0 <= scored["ai_score"] <= 100
    assert scored["ai_recommendation"] in {"advance", "hold", "reject"}
    assert scored["status"] == "scored"
    assert scored["ai_summary"]
    # strong keyword overlap -> should clear the advance threshold
    assert scored["ai_recommendation"] == "advance"


def test_scoring_missing_application_is_404(client):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/applications/{missing}/score").status_code == 404
