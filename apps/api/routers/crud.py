"""Generic CRUD router factory.

Every hiring entity exposes the same five operations, so we build them once
here and instantiate per table in :mod:`apps.api.main`. Each mutating
operation appends a row to ``ordinoxai.audit_logs`` via :func:`audit_event`.

Note: this module deliberately does *not* use ``from __future__ import
annotations``. The endpoint factories rely on the request/response model
*classes* being live annotation objects (not strings) so FastAPI can build
validation and OpenAPI from them.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from ..db import Database
from ..deps import get_db
from ..tables import TABLES

logger = logging.getLogger(__name__)

_RESERVED_QUERY = {"limit", "offset", "order_by", "order_dir"}


async def audit_event(
    db: Database,
    request: Request,
    entity_type: str,
    action: str,
    entity_id: UUID,
    old: Optional[dict],
    new: Optional[dict],
) -> None:
    """Record a mutation. Never raises — auditing must not fail a request."""
    await db.audit(
        entity_type=entity_type,
        action=action,
        entity_id=entity_id,
        old_data=jsonable_encoder(old) if old is not None else None,
        new_data=jsonable_encoder(new) if new is not None else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


def make_crud_router(
    *,
    table: str,
    prefix: str,
    tags: list[str],
    create_model: type[BaseModel],
    update_model: type[BaseModel],
    read_model: type[BaseModel],
    entity_type: Optional[str] = None,
) -> APIRouter:
    spec = TABLES[table]
    entity = entity_type or table  # audit_logs.entity_type label
    router = APIRouter(prefix=prefix, tags=tags)

    @router.post("", response_model=read_model, status_code=status.HTTP_201_CREATED)
    async def create(payload: create_model, request: Request, db: Database = Depends(get_db)):
        data = payload.model_dump(exclude_none=True)
        row = await db.insert(table, data)
        await audit_event(db, request, entity, "create", row["id"], None, row)
        return read_model(**row)

    @router.get("", response_model=list[read_model])
    async def list_rows(
        request: Request,
        db: Database = Depends(get_db),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        order_by: Optional[str] = Query(None),
        order_dir: str = Query("desc", pattern="^(asc|desc)$"),
    ):
        filters = {
            k: v
            for k, v in request.query_params.items()
            if k not in _RESERVED_QUERY and k in spec.filterable
        }
        rows = await db.list(
            table,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
        )
        return [read_model(**r) for r in rows]

    @router.get("/{row_id}", response_model=read_model)
    async def get_one(row_id: UUID, db: Database = Depends(get_db)):
        row = await db.get(table, row_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{entity} not found")
        return read_model(**row)

    @router.patch("/{row_id}", response_model=read_model)
    async def update(
        row_id: UUID, payload: update_model, request: Request, db: Database = Depends(get_db)
    ):
        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "no fields to update")
        before = await db.get(table, row_id)
        if before is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{entity} not found")
        row = await db.update(table, row_id, data)
        await audit_event(db, request, entity, "update", row_id, before, row)
        return read_model(**row)

    @router.delete("/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete(row_id: UUID, request: Request, db: Database = Depends(get_db)):
        before = await db.get(table, row_id)
        if before is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{entity} not found")
        await db.delete(table, row_id)
        await audit_event(db, request, entity, "delete", row_id, before, None)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
