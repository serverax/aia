from __future__ import annotations

from locust import HttpUser, between, task


class SyntheticEnterpriseUser(HttpUser):
    """Week 16 load profile for the deployed production-like cluster."""

    wait_time = between(0.2, 1.5)

    @task(5)
    def frontend_health(self) -> None:
        self.client.get("/health", name="frontend health")

    @task(4)
    def compliance_evaluate(self) -> None:
        self.client.post(
            "/compliance/evaluate",
            json={
                "agent_id": "domain_analyst_v1_20250520",
                "project_id": "sprint-8-load",
                "capability": "draft",
            },
            headers={
                "x-agent-id": "load_test_user",
                "x-project-id": "sprint-8-load",
                "x-capability": "policy_evaluation",
            },
            name="compliance policy evaluation",
        )

    @task(2)
    def readiness(self) -> None:
        self.client.get("/ready", name="readiness")
