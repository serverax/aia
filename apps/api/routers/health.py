"""Liveness and readiness probes.

These read ``app.state.db`` directly (rather than via the ``get_db``
dependency) so readiness can *report* an absent/unhealthy database as 503
instead of raising before the handler runs.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness probe (checks DB)")
async def readyz(request: Request, response: Response) -> dict[str, str]:
    db = getattr(request.app.state, "db", None)
    if db is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "no-database"}
    try:
        await db.ping()
    except Exception:  # noqa: BLE001 - any DB error means not ready
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "db-error"}
    return {"status": "ready"}
