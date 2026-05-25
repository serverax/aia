"""Unit tests for conflict detection (pure function — no Redis/PG)."""

from __future__ import annotations

import pytest

from libs.communication import ComplianceVerdict, RiskLevel
from services.orchestrator_agent.conflict import detect_conflicts

pytestmark = [pytest.mark.unit]


def test_no_conflicts_when_all_approve():
    conflicts = detect_conflicts(
        {
            "results": {
                "task_1": {
                    "verdict": ComplianceVerdict.APPROVED.value,
                    "risk_level": RiskLevel.GREEN.value,
                },
                "task_2": {"status": "completed"},
            }
        }
    )
    assert conflicts == []


def test_compliance_rejection_recorded():
    conflicts = detect_conflicts(
        {
            "results": {
                "task_1": {
                    "verdict": ComplianceVerdict.REJECTED.value,
                    "risk_level": RiskLevel.RED.value,
                    "rationale": "Breaches GDPR Art 6",
                },
            }
        }
    )
    assert len(conflicts) >= 1
    assert any(c.get("type") == "compliance_rejection" for c in conflicts)


def test_cross_agent_approval_conflict_recorded():
    conflicts = detect_conflicts(
        {
            "results": {
                "task_1": {
                    "verdict": ComplianceVerdict.REJECTED.value,
                    "risk_level": RiskLevel.RED.value,
                    "rationale": "GDPR violation",
                    "agent_id": "compliance_officer",
                },
                "task_2": {
                    "status": "completed",
                    "rationale": "Draft is complete",
                    "agent_id": "domain_analyst",
                },
            }
        }
    )
    types = {c.get("type") for c in conflicts}
    assert "approval_conflict" in types


def test_amber_alone_does_not_escalate():
    conflicts = detect_conflicts(
        {
            "results": {
                "task_1": {
                    "verdict": ComplianceVerdict.REQUIRES_REVISION.value,
                    "risk_level": RiskLevel.AMBER.value,
                },
            }
        }
    )
    # REQUIRES_REVISION isn't REJECTED and AMBER isn't RED — no escalation.
    assert conflicts == []
