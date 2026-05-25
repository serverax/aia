from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient

SERVICE_ROOT = Path(__file__).resolve().parents[2] / "services" / "compliance-service"
sys.path.insert(0, str(SERVICE_ROOT))

from compliance_service.kill_switch import KillSwitchPolicy
from compliance_service.main import app, state


@pytest.mark.unit
def test_kill_switch_api_blocks_after_update():
    asyncio.run(_assert_kill_switch_api_blocks_after_update())


async def _assert_kill_switch_api_blocks_after_update():
    state.replace(KillSwitchPolicy())
    async with AsyncClient(app=app, base_url="http://test") as client:
        update = await client.put(
            "/compliance/kill-switch",
            json={
                "global_enabled": True,
                "reason": "human compliance hold",
                "updated_by": "human_compliance_team",
            },
        )
        assert update.status_code == 200

        decision = await client.post("/compliance/evaluate", json={"agent_id": "analyst"})
        assert decision.status_code == 200
        assert decision.json()["allowed"] is False
        assert decision.json()["source"] == "SPRINTS-7-8-INSTRUCTIONS.md"
