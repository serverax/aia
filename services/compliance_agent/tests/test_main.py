"""Unit tests for compliance officer evaluation rules."""

from __future__ import annotations

import pytest

from libs.communication import ComplianceVerdict, RiskLevel
from services.compliance_agent.main import _evaluate

pytestmark = [pytest.mark.unit]


def test_clean_description_approved():
    result = _evaluate("Draft a standard purchase order", {})
    assert result.verdict is ComplianceVerdict.APPROVED
    assert result.risk_level is RiskLevel.GREEN
    assert result.flags == []


def test_personal_data_amber():
    result = _evaluate("Collect personal data for marketing", {})
    assert result.verdict is ComplianceVerdict.REQUIRES_REVISION
    assert result.risk_level is RiskLevel.AMBER
    assert "personal data" in result.flags


def test_violation_keyword_rejected():
    result = _evaluate("Highlight any violation of policy", {})
    assert result.verdict is ComplianceVerdict.REJECTED
    assert result.risk_level is RiskLevel.RED
    assert "violation" in result.flags


def test_reject_beats_amber_when_both_present():
    """If a description triggers both reject and amber rules, reject wins."""
    result = _evaluate("Personal data exported in violation of GDPR", {})
    assert result.verdict is ComplianceVerdict.REJECTED


def test_inputs_are_inspected_too():
    result = _evaluate("benign", {"clause": "transfer to third country without consent"})
    assert result.verdict is ComplianceVerdict.REJECTED
