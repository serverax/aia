"""Kill-switch policy model and deterministic evaluator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class KillSwitchPolicy:
    global_enabled: bool = False
    disabled_agents: frozenset[str] = frozenset()
    disabled_projects: frozenset[str] = frozenset()
    disabled_capabilities: frozenset[str] = frozenset()
    reason: str = ""
    source: str = "SPRINTS-7-8-INSTRUCTIONS.md"
    updated_by: str = "system"
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class KillSwitchDecision:
    allowed: bool
    reason: str
    source: str
    policy_version: str


class KillSwitchState:
    """Pure policy evaluator used by the API and middleware."""

    def __init__(self, policy: KillSwitchPolicy | None = None) -> None:
        self._policy = policy or KillSwitchPolicy()

    @property
    def policy(self) -> KillSwitchPolicy:
        return self._policy

    @property
    def version(self) -> str:
        parts = [
            self._policy.updated_at.astimezone(timezone.utc).isoformat(),
            self._policy.updated_by,
            str(self._policy.global_enabled),
            ",".join(sorted(self._policy.disabled_agents)),
            ",".join(sorted(self._policy.disabled_projects)),
            ",".join(sorted(self._policy.disabled_capabilities)),
        ]
        return "|".join(parts)

    def replace(self, policy: KillSwitchPolicy) -> None:
        self._policy = policy

    def evaluate(
        self,
        *,
        agent_id: str | None = None,
        project_id: str | None = None,
        capability: str | None = None,
    ) -> KillSwitchDecision:
        if self._policy.global_enabled:
            return KillSwitchDecision(False, self._policy.reason, self._policy.source, self.version)
        if agent_id and agent_id in self._policy.disabled_agents:
            return KillSwitchDecision(
                False, f"agent disabled: {agent_id}", self._policy.source, self.version
            )
        if project_id and project_id in self._policy.disabled_projects:
            return KillSwitchDecision(
                False, f"project disabled: {project_id}", self._policy.source, self.version
            )
        if capability and capability in self._policy.disabled_capabilities:
            return KillSwitchDecision(
                False, f"capability disabled: {capability}", self._policy.source, self.version
            )
        return KillSwitchDecision(True, "allowed", self._policy.source, self.version)
