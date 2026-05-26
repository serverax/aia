"""FastAPI dependencies resolving shared singletons off ``app.state``.

Tests override these (``app.dependency_overrides``) to inject a
:class:`~apps.api.db.FakeDatabase` and a stub scorer.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from .db import Database
from .scoring import Scorer


def get_db(request: Request) -> Database:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "database connection unavailable")
    return db


def get_scorer(request: Request) -> Scorer:
    scorer = getattr(request.app.state, "scorer", None)
    if scorer is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "scorer unavailable")
    return scorer
