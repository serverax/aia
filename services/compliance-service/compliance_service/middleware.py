"""FastAPI middleware enforcing the active compliance kill switch."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from compliance_service.kill_switch import KillSwitchState


class ComplianceMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        state: KillSwitchState,
        exempt_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.state = state
        self.exempt_paths = exempt_paths or {"/health", "/ready", "/compliance/kill-switch"}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        decision = self.state.evaluate(
            agent_id=request.headers.get("x-agent-id"),
            project_id=request.headers.get("x-project-id"),
            capability=request.headers.get("x-capability"),
        )
        if not decision.allowed:
            return JSONResponse(
                status_code=423,
                content={
                    "status": "blocked",
                    "reason": decision.reason,
                    "source": decision.source,
                    "policy_version": decision.policy_version,
                },
            )

        response = await call_next(request)
        response.headers["x-compliance-policy-version"] = decision.policy_version
        return response
