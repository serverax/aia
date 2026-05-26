"""Compliance gate: consult the kill-switch before routing/executing work.

The Compliance Service (``services/compliance-service``) owns the kill-switch
policy and exposes ``POST /compliance/evaluate`` returning::

    {"allowed": bool, "reason": str, "source": str, "policy_version": str}

This module is the *client* side of that contract. The orchestrator calls
:meth:`ComplianceGate.check` before dispatching a task to a specialist agent;
if the gate denies, the task is rejected instead of executed.

Design notes
------------
* **Injectable evaluator.** Like ``libs.llm.StubLLMClient``, the network call
  is hidden behind an async callable so unit tests run without a live service.
* **Fail-closed by default.** If the compliance service is unreachable, a
  kill-switch you cannot read must be treated as *engaged* — we deny and let a
  human investigate. Flip ``fail_closed=False`` only where availability beats
  safety. The decision records ``source="gate-unreachable"`` so it's auditable.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# An evaluator takes the JSON body for /compliance/evaluate and returns the
# parsed JSON response. Injected in tests; defaults to an httpx call.
Evaluator = Callable[[dict], Awaitable[dict]]


class ComplianceDecision(BaseModel):
    allowed: bool
    reason: str
    source: str
    policy_version: str = ""


class ComplianceGate:
    """Client for the Compliance Service kill-switch evaluation endpoint."""

    def __init__(
        self,
        base_url: str = "http://compliance-service:8000",
        *,
        fail_closed: bool = True,
        timeout: float = 2.0,
        evaluator: Optional[Evaluator] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._fail_closed = fail_closed
        self._timeout = timeout
        self._evaluator = evaluator or self._http_evaluate

    async def _http_evaluate(self, body: dict) -> dict:
        # Imported lazily so importing this module never hard-requires httpx
        # and the orchestrator can run with an injected evaluator in tests.
        import httpx

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/compliance/evaluate", json=body)
            resp.raise_for_status()
            return resp.json()

    async def check(
        self,
        *,
        agent_id: str | None = None,
        project_id: str | None = None,
        capability: str | None = None,
    ) -> ComplianceDecision:
        """Return the kill-switch decision for this (agent, project, capability).

        On transport failure, honour ``fail_closed``: deny if True (default),
        allow-with-warning if False. Either way the decision is auditable.
        """
        body = {"agent_id": agent_id, "project_id": project_id, "capability": capability}
        try:
            data = await self._evaluator(body)
            return ComplianceDecision(
                allowed=bool(data["allowed"]),
                reason=str(data.get("reason", "")),
                source=str(data.get("source", "compliance-service")),
                policy_version=str(data.get("policy_version", "")),
            )
        except Exception as exc:  # network error, 5xx, malformed payload
            logger.error("compliance gate unreachable: %s (fail_closed=%s)", exc, self._fail_closed)
            return ComplianceDecision(
                allowed=not self._fail_closed,
                reason=f"compliance service unreachable: {exc}",
                source="gate-unreachable",
            )
