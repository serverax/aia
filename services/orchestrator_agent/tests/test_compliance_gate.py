"""Unit tests for ComplianceGate using an injected (stub) evaluator.

No network or live Compliance Service required — mirrors the StubLLMClient
pattern used elsewhere in the repo.
"""

from __future__ import annotations

import pytest

from services.orchestrator_agent.compliance_gate import ComplianceDecision, ComplianceGate

pytestmark = [pytest.mark.unit]


@pytest.mark.asyncio
async def test_allows_when_policy_open():
    async def evaluator(body):
        return {"allowed": True, "reason": "allowed", "source": "test", "policy_version": "v1"}

    gate = ComplianceGate(evaluator=evaluator)
    decision = await gate.check(agent_id="analyst-v1", project_id="p1")

    assert isinstance(decision, ComplianceDecision)
    assert decision.allowed is True
    assert decision.policy_version == "v1"


@pytest.mark.asyncio
async def test_denies_when_agent_disabled():
    async def evaluator(body):
        assert body["agent_id"] == "analyst-v1"
        return {"allowed": False, "reason": "agent disabled: analyst-v1", "source": "test"}

    gate = ComplianceGate(evaluator=evaluator)
    decision = await gate.check(agent_id="analyst-v1")

    assert decision.allowed is False
    assert "disabled" in decision.reason


@pytest.mark.asyncio
async def test_fail_closed_denies_on_transport_error():
    async def evaluator(body):
        raise ConnectionError("connection refused")

    gate = ComplianceGate(fail_closed=True, evaluator=evaluator)
    decision = await gate.check(agent_id="analyst-v1")

    assert decision.allowed is False
    assert decision.source == "gate-unreachable"


@pytest.mark.asyncio
async def test_fail_open_allows_on_transport_error():
    async def evaluator(body):
        raise TimeoutError("timed out")

    gate = ComplianceGate(fail_closed=False, evaluator=evaluator)
    decision = await gate.check(capability="web_search")

    assert decision.allowed is True
    assert decision.source == "gate-unreachable"


# --- Orchestrator admission-gate wiring -------------------------------------
# Construct the service via __new__ to avoid building real Redis/OTel/LLM
# clients; we only exercise handle_request's gate branch.


def _bare_service(gate, graph=None):
    from services.orchestrator_agent.main import OrchestratorService, Settings

    svc = OrchestratorService.__new__(OrchestratorService)
    svc.settings = Settings()
    svc.compliance_gate = gate
    svc.graph = graph
    return svc


@pytest.mark.asyncio
async def test_handle_request_short_circuits_when_denied():
    from services.orchestrator_agent.main import RequestPayload

    denying = ComplianceGate(evaluator=lambda body: _deny())
    svc = _bare_service(denying, graph=None)  # graph must NOT be touched

    state = await svc.handle_request(RequestPayload(user_request="x", project_id="p1"))

    assert state["current_phase"] == "rejected_by_compliance"
    assert state["compliance"]["allowed"] is False


@pytest.mark.asyncio
async def test_handle_request_proceeds_when_allowed():
    from services.orchestrator_agent.main import RequestPayload

    class FakeGraph:
        def __init__(self):
            self.called = False

        async def ainvoke(self, initial):
            self.called = True
            return {**initial, "current_phase": "complete"}

    allowing = ComplianceGate(evaluator=lambda body: _allow())
    graph = FakeGraph()
    svc = _bare_service(allowing, graph=graph)

    state = await svc.handle_request(RequestPayload(user_request="x", project_id="p1"))

    assert graph.called is True
    assert state["current_phase"] == "complete"


@pytest.mark.asyncio
async def test_handle_request_no_gate_is_backwards_compatible():
    from services.orchestrator_agent.main import RequestPayload

    class FakeGraph:
        async def ainvoke(self, initial):
            return {**initial, "current_phase": "complete"}

    svc = _bare_service(None, graph=FakeGraph())  # gating disabled
    state = await svc.handle_request(RequestPayload(user_request="x"))
    assert state["current_phase"] == "complete"


async def _deny():
    return {"allowed": False, "reason": "project disabled: p1", "source": "test"}


async def _allow():
    return {"allowed": True, "reason": "allowed", "source": "test"}
