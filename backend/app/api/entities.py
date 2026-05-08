from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.deps import require_admin, require_member
from app.db import get_db
from app.models.entity import Entity
from app.models.entity_pattern import EntityPattern
from app.models.enums import EntityType, PatternSource
from app.pipeline.entity_resolver import normalize_entity
from app.schemas.entity import (
    EntityCreate,
    EntityDetail,
    EntityListResponse,
    EntityOut,
    EntityUpdate,
    PatternCreate,
    EntityPatternOut,
)
from app.schemas.common import MessageResponse

router = APIRouter()


@router.get("/entities", response_model=EntityListResponse, dependencies=[Depends(require_member)])
async def list_entities(
    entity_type: EntityType | None = Query(None, alias="type"),
    search: str | None = None,
    confirmed: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Entity)
    if entity_type:
        q = q.where(Entity.type == entity_type)
    if confirmed is not None:
        q = q.where(Entity.confirmed == confirmed)
    if search:
        q = q.where(Entity.canonical_name.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (
        await db.execute(
            q.order_by(Entity.canonical_name).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()

    return EntityListResponse(
        items=[EntityOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/entities/{entity_id}", response_model=EntityDetail, dependencies=[Depends(require_member)])
async def get_entity(entity_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(
            select(Entity).options(selectinload(Entity.patterns)).where(Entity.id == entity_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    return EntityDetail.model_validate(row)


@router.post("/entities", response_model=EntityOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_entity(body: EntityCreate, db: AsyncSession = Depends(get_db)):
    entity = Entity(
        canonical_name=body.canonical_name,
        display_name=body.display_name,
        type=body.type,
        confirmed=body.confirmed,
    )
    db.add(entity)
    await db.flush()
    return EntityOut.model_validate(entity)


@router.patch("/entities/{entity_id}", response_model=EntityOut, dependencies=[Depends(require_admin)])
async def update_entity(
    entity_id: UUID, body: EntityUpdate, db: AsyncSession = Depends(get_db)
):
    row = (await db.execute(select(Entity).where(Entity.id == entity_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)

    await db.flush()
    return EntityOut.model_validate(row)


@router.post(
    "/entities/{entity_id}/patterns",
    response_model=EntityPatternOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
async def add_pattern(
    entity_id: UUID, body: PatternCreate, db: AsyncSession = Depends(get_db)
):
    entity = (await db.execute(select(Entity).where(Entity.id == entity_id))).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")

    normalized = normalize_entity(body.pattern)
    existing = (
        await db.execute(
            select(EntityPattern).where(
                EntityPattern.entity_id == entity_id,
                EntityPattern.normalized == normalized,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="El patrón ya existe para esta entidad")

    pattern = EntityPattern(
        entity_id=entity_id,
        pattern=body.pattern,
        normalized=normalized,
        source=body.source,
    )
    db.add(pattern)
    await db.flush()
    return EntityPatternOut.model_validate(pattern)


@router.delete(
    "/entities/{entity_id}/patterns/{pattern_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_admin)],
)
async def delete_pattern(
    entity_id: UUID, pattern_id: UUID, db: AsyncSession = Depends(get_db)
):
    row = (
        await db.execute(
            select(EntityPattern).where(
                EntityPattern.id == pattern_id,
                EntityPattern.entity_id == entity_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Patrón no encontrado")

    await db.delete(row)
    return MessageResponse(message="Patrón eliminado")
