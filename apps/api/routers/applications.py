"""Applications router: standard CRUD plus the AI candidate-scoring endpoint.

``POST /applications/{id}/score`` pulls the application with its job and
candidate, runs the configured :class:`~apps.api.scoring.Scorer`, persists the
``ai_*`` columns, moves the application to ``status='scored'``, and audits it.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import schemas
from ..db import Database
from ..deps import get_db, get_scorer
from ..scoring import Scorer
from .crud import audit_event, make_crud_router

router: APIRouter = make_crud_router(
    table="applications",
    prefix="/applications",
    tags=["applications"],
    create_model=schemas.ApplicationCreate,
    update_model=schemas.ApplicationUpdate,
    read_model=schemas.ApplicationRead,
)


@router.post(
    "/{row_id}/score",
    response_model=schemas.ApplicationRead,
    tags=["applications"],
    summary="Run AI scoring for an application",
)
async def score_application(
    row_id: UUID,
    request: Request,
    db: Database = Depends(get_db),
    scorer: Scorer = Depends(get_scorer),
):
    application = await db.get("applications", row_id)
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "application not found")

    job_id = application.get("job_id")
    candidate_id = application.get("candidate_id")
    job = (await db.get("jobs", job_id)) if job_id else None
    candidate = (await db.get("candidates", candidate_id)) if candidate_id else None
    if job is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "application's job no longer exists")
    if candidate is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "application's candidate no longer exists")

    result = await scorer.score(job=job, application=application, candidate=candidate)
    update = {
        "ai_score": result.score,
        "ai_summary": result.summary,
        "ai_risk_flags": result.risk_flags,
        "ai_recommendation": result.recommendation,
        "status": "scored",
    }
    before = dict(application)
    row = await db.update("applications", row_id, update)
    await audit_event(db, request, "applications", "score", row_id, before, row)
    return schemas.ApplicationRead(**row)
