from __future__ import annotations

import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[2] / "services" / "compliance-service"
sys.path.insert(0, str(SERVICE_ROOT))

from compliance_service.kill_switch import KillSwitchPolicy, KillSwitchState


@pytest.mark.unit
def test_global_kill_switch_blocks_everything():
    state = KillSwitchState(
        KillSwitchPolicy(
            global_enabled=True,
            reason="human compliance hold",
            updated_by="human_compliance_team",
        )
    )

    decision = state.evaluate(agent_id="domain_analyst", project_id="client-a", capability="draft")

    assert decision.allowed is False
    assert decision.reason == "human compliance hold"
    assert decision.source == "SPRINTS-7-8-INSTRUCTIONS.md"


@pytest.mark.unit
def test_targeted_kill_switch_blocks_agent_project_and_capability():
    state = KillSwitchState(
        KillSwitchPolicy(
            disabled_agents=frozenset({"agent-a"}),
            disabled_projects=frozenset({"project-a"}),
            disabled_capabilities=frozenset({"external_send"}),
            reason="targeted hold",
            updated_by="compliance",
        )
    )

    assert state.evaluate(agent_id="agent-a").allowed is False
    assert state.evaluate(project_id="project-a").allowed is False
    assert state.evaluate(capability="external_send").allowed is False
    assert (
        state.evaluate(agent_id="agent-b", project_id="project-b", capability="draft").allowed
        is True
    )
