from __future__ import annotations

import json
import random
import time
from typing import Any, Dict, Iterable, Optional

from locust import HttpUser, between, events, task

JSON_HEADERS = {
    "content-type": "application/json",
    "accept": "application/json",
}

SCENARIO_PAYLOADS = {
    "smoke": [
        {
            "agent_id": "domain_analyst_v1_20250520",
            "project_id": "sprint-8-smoke",
            "capability": "draft",
        }
    ],
    "baseline": [
        {
            "agent_id": "orchestrator_v1_20250520",
            "project_id": "sprint-8-baseline",
            "capability": "route_task",
        },
        {
            "agent_id": "compliance_officer_v1_20250520",
            "project_id": "sprint-8-baseline",
            "capability": "policy_evaluation",
        },
    ],
    "business_mix": [
        {
            "agent_id": "domain_analyst_v1_20250520",
            "project_id": "client-alpha",
            "capability": "draft",
        },
        {
            "agent_id": "editor_v1_20250520",
            "project_id": "client-alpha",
            "capability": "format_document",
        },
        {
            "agent_id": "orchestrator_v1_20250520",
            "project_id": "client-beta",
            "capability": "assign_task",
        },
        {
            "agent_id": "compliance_officer_v1_20250520",
            "project_id": "client-beta",
            "capability": "external_send",
        },
    ],
    "production": [
        {
            "agent_id": "domain_analyst_v1_20250520",
            "project_id": "sprint-8-prod",
            "capability": "draft",
        },
        {
            "agent_id": "editor_v1_20250520",
            "project_id": "sprint-8-prod",
            "capability": "format_document",
        },
        {
            "agent_id": "orchestrator_v1_20250520",
            "project_id": "sprint-8-prod",
            "capability": "assign_task",
        },
        {
            "agent_id": "compliance_officer_v1_20250520",
            "project_id": "sprint-8-prod",
            "capability": "external_send",
        },
    ],
}


def _json_or_empty(response: Any) -> Dict[str, Any]:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return {}
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _require_fields(payload: Dict[str, Any], fields: Iterable[str]) -> Optional[str]:
    missing = [field for field in fields if field not in payload]
    if missing:
        return f"missing response fields: {', '.join(missing)}"
    return None


def _policy_payload(seed: Dict[str, str]) -> Dict[str, Any]:
    return {
        "agent_id": seed["agent_id"],
        "project_id": seed["project_id"],
        "capability": seed["capability"],
        "action": "evaluate_compliance_policy",
        "policy_context": {
            "jurisdiction": "UK",
            "data_classification": "confidential",
            "client_data_scope": "project_only",
            "human_approval_required": seed["capability"] in {"external_send", "assign_task"},
        },
        "request": {
            "document_type": "settlement_agreement",
            "operation": seed["capability"],
            "source": "sprint-8-load-test",
        },
    }


def _decision_payload(seed: Dict[str, str]) -> Dict[str, Any]:
    return {
        "decision_id": f"{seed['project_id']}-{seed['agent_id']}-{seed['capability']}",
        "agent_id": seed["agent_id"],
        "project_id": seed["project_id"],
        "capability": seed["capability"],
        "include_sources": True,
        "include_policy_trace": True,
    }


def _headers(seed: Dict[str, str]) -> Dict[str, str]:
    headers = dict(JSON_HEADERS)
    headers.update(
        {
            "x-agent-id": seed["agent_id"],
            "x-project-id": seed["project_id"],
            "x-capability": seed["capability"],
        }
    )
    return headers


class ComplianceLoadUser(HttpUser):
    abstract = True
    wait_time = between(0.1, 1.0)
    scenario_name = "business_mix"
    payloads = SCENARIO_PAYLOADS["business_mix"]

    def choose_seed(self) -> Dict[str, str]:
        return random.choice(self.payloads)

    def record_compliance_latency(
        self, started_at: float, exception: Optional[Exception] = None
    ) -> None:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        events.request.fire(
            request_type="CUSTOM",
            name="compliance_check_latency",
            response_time=elapsed_ms,
            response_length=0,
            exception=exception,
            context={"scenario": self.scenario_name},
        )

    def post_compliance_evaluate(self) -> None:
        seed = self.choose_seed()
        started_at = time.perf_counter()
        metric_exception: Optional[Exception] = None
        with self.client.post(
            "/compliance/evaluate",
            json=_policy_payload(seed),
            headers=_headers(seed),
            name="POST /compliance/evaluate",
            catch_response=True,
        ) as response:
            payload = _json_or_empty(response)
            failure = _require_fields(payload, ["allowed", "reason", "policy_version"])
            if response.status_code != 200:
                metric_exception = RuntimeError(f"HTTP {response.status_code}")
                response.failure(f"expected HTTP 200, got {response.status_code}")
            elif failure:
                metric_exception = RuntimeError(failure)
                response.failure(failure)
            else:
                response.success()
        self.record_compliance_latency(started_at, metric_exception)

    def get_approvals(self) -> None:
        seed = self.choose_seed()
        with self.client.get(
            "/approvals",
            params={"project_id": seed["project_id"], "agent_id": seed["agent_id"], "limit": "25"},
            headers={"accept": "application/json", "x-project-id": seed["project_id"]},
            name="GET /approvals",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 204):
                response.success()
            else:
                response.failure(f"expected HTTP 200/204, got {response.status_code}")

    def get_audit_trail(self) -> None:
        seed = self.choose_seed()
        with self.client.get(
            "/audit/trail",
            params={"project_id": seed["project_id"], "agent_id": seed["agent_id"], "limit": "50"},
            headers={"accept": "application/json", "x-project-id": seed["project_id"]},
            name="GET /audit/trail",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"expected HTTP 200, got {response.status_code}")

    def post_decision_explain(self) -> None:
        seed = self.choose_seed()
        with self.client.post(
            "/decision/explain",
            json=_decision_payload(seed),
            headers=_headers(seed),
            name="POST /decision/explain",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected HTTP 200, got {response.status_code}")
                return

            payload = _json_or_empty(response)
            if not payload:
                response.failure("empty or non-object JSON response")
            else:
                response.success()


class SmokeTestUser(ComplianceLoadUser):
    """5 users, 1 user/sec ramp, short validation run."""

    weight = 1
    wait_time = between(0.8, 1.2)
    scenario_name = "smoke"
    payloads = SCENARIO_PAYLOADS["smoke"]

    @task(8)
    def evaluate(self) -> None:
        self.post_compliance_evaluate()

    @task(1)
    def approvals(self) -> None:
        self.get_approvals()

    @task(1)
    def audit_trail(self) -> None:
        self.get_audit_trail()

    @task(1)
    def decision_explain(self) -> None:
        self.post_decision_explain()


class BaselineUser(ComplianceLoadUser):
    """10 users, 2 users/sec ramp, low-concurrency baseline."""

    weight = 2
    wait_time = between(0.35, 0.65)
    scenario_name = "baseline"
    payloads = SCENARIO_PAYLOADS["baseline"]

    @task(7)
    def evaluate(self) -> None:
        self.post_compliance_evaluate()

    @task(2)
    def approvals(self) -> None:
        self.get_approvals()

    @task(2)
    def audit_trail(self) -> None:
        self.get_audit_trail()

    @task(2)
    def decision_explain(self) -> None:
        self.post_decision_explain()


class BusinessMixUser(ComplianceLoadUser):
    """50 users, realistic compliance traffic distribution."""

    weight = 6
    wait_time = between(0.1, 0.4)
    scenario_name = "business_mix"
    payloads = SCENARIO_PAYLOADS["business_mix"]

    @task(10)
    def evaluate(self) -> None:
        self.post_compliance_evaluate()

    @task(3)
    def approvals(self) -> None:
        self.get_approvals()

    @task(4)
    def audit_trail(self) -> None:
        self.get_audit_trail()

    @task(4)
    def decision_explain(self) -> None:
        self.post_decision_explain()


class ProductionTargetUser(ComplianceLoadUser):
    """1000 users, sustained Sprint 8 production target."""

    weight = 10
    wait_time = between(0.02, 0.2)
    scenario_name = "production"
    payloads = SCENARIO_PAYLOADS["production"]

    @task(12)
    def evaluate(self) -> None:
        self.post_compliance_evaluate()

    @task(3)
    def approvals(self) -> None:
        self.get_approvals()

    @task(5)
    def audit_trail(self) -> None:
        self.get_audit_trail()

    @task(5)
    def decision_explain(self) -> None:
        self.post_decision_explain()
