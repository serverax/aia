"""Sprint 7 Compliance Service.

Provides the kill-switch API and policy evaluation surface. Production
validation is intentionally gated on the real Week 14-15 cluster.
"""

from __future__ import annotations

from datetime import datetime, timezone

from compliance_service.kill_switch import KillSwitchPolicy, KillSwitchState
from fastapi import FastAPI, HTTPException, Security
from pydantic import BaseModel, Field

from libs.auth import User, get_current_active_user


class KillSwitchRequest(BaseModel):
    global_enabled: bool = False
    disabled_agents: list[str] = Field(default_factory=list)
    disabled_projects: list[str] = Field(default_factory=list)
    disabled_capabilities: list[str] = Field(default_factory=list)
    reason: str
    updated_by: str
    source: str = "SPRINTS-7-8-INSTRUCTIONS.md"


class EvaluateRequest(BaseModel):
    agent_id: str | None = None
    project_id: str | None = None
    capability: str | None = None


state = KillSwitchState()
app = FastAPI(title="Compliance Service", version="0.1.0")


def _policy_payload(policy: KillSwitchPolicy) -> dict[str, object]:
    return {
        "global_enabled": policy.global_enabled,
        "disabled_agents": sorted(policy.disabled_agents),
        "disabled_projects": sorted(policy.disabled_projects),
        "disabled_capabilities": sorted(policy.disabled_capabilities),
        "reason": policy.reason,
        "source": policy.source,
        "updated_by": policy.updated_by,
        "updated_at": policy.updated_at.astimezone(timezone.utc).isoformat(),
        "policy_version": state.version,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready", "cluster_validation": "required"}


@app.get("/compliance/kill-switch")
async def get_kill_switch() -> dict[str, object]:
    return _policy_payload(state.policy)


@app.put("/compliance/kill-switch")
async def put_kill_switch(
    request: KillSwitchRequest,
    _user: User = Security(get_current_active_user, scopes=["admin"]),
) -> dict[str, object]:
    # Mutating the kill-switch requires an authenticated admin (scope "admin").
    # GET and /compliance/evaluate stay open so the orchestrator gate can read.
    if request.global_enabled and not request.reason.strip():
        raise HTTPException(
            status_code=400, detail="reason is required when enabling global kill switch"
        )
    policy = KillSwitchPolicy(
        global_enabled=request.global_enabled,
        disabled_agents=frozenset(request.disabled_agents),
        disabled_projects=frozenset(request.disabled_projects),
        disabled_capabilities=frozenset(request.disabled_capabilities),
        reason=request.reason,
        source=request.source,
        updated_by=request.updated_by,
        updated_at=datetime.now(timezone.utc),
    )
    state.replace(policy)
    return _policy_payload(policy)


@app.post("/compliance/evaluate")
async def evaluate(request: EvaluateRequest) -> dict[str, object]:
    decision = state.evaluate(
        agent_id=request.agent_id,
        project_id=request.project_id,
        capability=request.capability,
    )
    return {
        "allowed": decision.allowed,
        "reason": decision.reason,
        "source": decision.source,
        "policy_version": decision.policy_version,
    }
