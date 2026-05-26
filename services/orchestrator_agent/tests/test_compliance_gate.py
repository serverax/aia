"""Unit tests for ComplianceGate using an injected (stub) evaluator.

No network or live Compliance Service required — mirrors the StubLLMClient
pattern used elsewhere in the repo.
"""

from __future__ import annotations

import pytest

from services.orchestrator_agent.compliance_gate import ComplianceDecision, ComplianceGate


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
