from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[2] / "services" / "compliance-service"
sys.path.insert(0, str(SERVICE_ROOT))

from compliance_service.audit_chain import AuditChainEntry, build_audit_hash, verify_audit_chain


@pytest.mark.unit
def test_audit_chain_detects_payload_tampering():
    timestamp = datetime(2026, 5, 21, tzinfo=timezone.utc)
    first_hash = build_audit_hash(
        previous_hash=None,
        timestamp=timestamp,
        agent_id="compliance_officer_v1_20250520",
        event_type="kill_switch_update",
        decision="approved",
        reason="human compliance hold",
        source="SPRINTS-7-8-INSTRUCTIONS.md",
        payload={"global_enabled": True},
    )
    second_hash = build_audit_hash(
        previous_hash=first_hash,
        timestamp=timestamp,
        agent_id="compliance_officer_v1_20250520",
        event_type="policy_evaluation",
        decision="blocked",
        reason="human compliance hold",
        source="SPRINTS-7-8-INSTRUCTIONS.md",
        payload={"agent_id": "analyst"},
    )
    valid_chain = [
        AuditChainEntry(
            timestamp,
            "compliance_officer_v1_20250520",
            "kill_switch_update",
            "approved",
            "human compliance hold",
            "SPRINTS-7-8-INSTRUCTIONS.md",
            {"global_enabled": True},
            None,
            first_hash,
        ),
        AuditChainEntry(
            timestamp,
            "compliance_officer_v1_20250520",
            "policy_evaluation",
            "blocked",
            "human compliance hold",
            "SPRINTS-7-8-INSTRUCTIONS.md",
            {"agent_id": "analyst"},
            first_hash,
            second_hash,
        ),
    ]

    assert verify_audit_chain(valid_chain) == (True, None)

    tampered_chain = [
        valid_chain[0],
        AuditChainEntry(
            timestamp,
            "compliance_officer_v1_20250520",
            "policy_evaluation",
            "blocked",
            "human compliance hold",
            "SPRINTS-7-8-INSTRUCTIONS.md",
            {"agent_id": "editor"},
            first_hash,
            second_hash,
        ),
    ]
    assert verify_audit_chain(tampered_chain) == (False, 1)
