"""Unresolved entity inbox.

Users review raw entity names the pipeline couldn't match and either:
  - Link them to an existing entity (POST .../resolve)
  - Create a new entity from the name (POST .../create-entity)
  - Dismiss them (POST .../ignore)

Resolving or creating also adds an EntityPattern so future occurrences
auto-link without human review.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin, require_member
from app.db import get_db
from app.models.entity import Entity
from app.models.entity_pattern import EntityPattern
from app.models.enums import PatternSource, UnresolvedEntityStatus
from app.models.unresolved_entity_name import UnresolvedEntityName
from app.pipeline.entity_resolver import normalize_entity
from app.schemas.common import MessageResponse
from app.schemas.entity import EntityOut
from app.schemas.unresolved_entity import (
    CreateEntityRequest,
    ResolveRequest,
    UnresolvedEntityOut,
    UnresolvedListResponse,
)

router = APIRouter()


@router.get(
    "/unresolved-entities",
    response_model=UnresolvedListResponse,
    dependencies=[Depends(require_member)],
)
async def list_unresolved(
    status: UnresolvedEntityStatus | None = UnresolvedEntityStatus.pending,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(UnresolvedEntityName)
    if status:
        q = q.where(UnresolvedEntityName.status == status)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (
        await db.execute(
            q.order_by(UnresolvedEntityName.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return UnresolvedListResponse(
        items=[UnresolvedEntityOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/unresolved-entities/{item_id}/resolve",
    response_model=MessageResponse,
    dependencies=[Depends(require_admin)],
)
async def resolve_to_existing(
    item_id: UUID, body: ResolveRequest, db: AsyncSession = Depends(get_db)
):
    """Link this unresolved name to an existing entity and add a pattern."""
    item = await _get_pending(item_id, db)

    entity = (await db.execute(select(Entity).where(Entity.id == body.entity_id))).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")

    await _upsert_pattern(item.normalized, item.raw_name, entity.id, db)

    item.status = UnresolvedEntityStatus.matched
    item.resolved_entity_id = entity.id
    await db.flush()
    return MessageResponse(message="Nombre vinculado a entidad existente")


@router.post(
    "/unresolved-entities/{item_id}/create-entity",
    response_model=EntityOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
async def create_entity_from_unresolved(
    item_id: UUID, body: CreateEntityRequest, db: AsyncSession = Depends(get_db)
):
    """Create a new entity from this unresolved name."""
    item = await _get_pending(item_id, db)

    entity = Entity(
        canonical_name=body.canonical_name,
        display_name=body.display_name,
        type=body.type,
        confirmed=True,
    )
    db.add(entity)
    await db.flush()

    await _upsert_pattern(item.normalized, item.raw_name, entity.id, db)

    item.status = UnresolvedEntityStatus.created
    item.resolved_entity_id = entity.id
    await db.flush()
    return EntityOut.model_validate(entity)


@router.post(
    "/unresolved-entities/{item_id}/ignore",
    response_model=MessageResponse,
    dependencies=[Depends(require_admin)],
)
async def ignore_unresolved(item_id: UUID, db: AsyncSession = Depends(get_db)):
    item = await _get_pending(item_id, db)
    item.status = UnresolvedEntityStatus.ignored
    await db.flush()
    return MessageResponse(message="Nombre descartado")


async def _get_pending(item_id: UUID, db: AsyncSession) -> UnresolvedEntityName:
    row = (
        await db.execute(select(UnresolvedEntityName).where(UnresolvedEntityName.id == item_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Elemento no encontrado")
    if row.status != UnresolvedEntityStatus.pending:
        raise HTTPException(
            status_code=409,
            detail=f"Este elemento ya fue procesado (estado: {row.status.value})",
        )
    return row


async def _upsert_pattern(normalized: str, raw: str, entity_id: UUID, db: AsyncSession) -> None:
    existing = (
        await db.execute(
            select(EntityPattern).where(
                EntityPattern.entity_id == entity_id,
                EntityPattern.normalized == normalized,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return
    pattern = EntityPattern(
        entity_id=entity_id,
        pattern=raw,
        normalized=normalized,
        source=PatternSource.user_added,
    )
    db.add(pattern)
    await db.flush()
