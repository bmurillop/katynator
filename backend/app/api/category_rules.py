from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin, require_member
from app.db import get_db
from app.models.category_rule import CategoryRule
from app.schemas.category_rule import CategoryRuleCreate, CategoryRuleOut, CategoryRuleUpdate
from app.schemas.common import MessageResponse

router = APIRouter()


@router.get("/category-rules", response_model=list[CategoryRuleOut], dependencies=[Depends(require_member)])
async def list_rules(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(select(CategoryRule).order_by(CategoryRule.priority.desc()))
    ).scalars().all()
    return [CategoryRuleOut.model_validate(r) for r in rows]


@router.post("/category-rules", response_model=CategoryRuleOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_rule(body: CategoryRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = CategoryRule(
        entity_id=body.entity_id,
        memo_pattern=body.memo_pattern,
        match_type=body.match_type,
        category_id=body.category_id,
        priority=body.priority,
        source=body.source,
    )
    db.add(rule)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una regla con esa combinación de entidad/patrón/tipo")

    return CategoryRuleOut.model_validate(rule)


@router.patch("/category-rules/{rule_id}", response_model=CategoryRuleOut, dependencies=[Depends(require_admin)])
async def update_rule(
    rule_id: UUID, body: CategoryRuleUpdate, db: AsyncSession = Depends(get_db)
):
    row = (
        await db.execute(select(CategoryRule).where(CategoryRule.id == rule_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)

    await db.commit()
    return CategoryRuleOut.model_validate(row)


@router.delete("/category-rules/{rule_id}", response_model=MessageResponse, dependencies=[Depends(require_admin)])
async def delete_rule(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(select(CategoryRule).where(CategoryRule.id == rule_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    await db.delete(row)
    return MessageResponse(message="Regla eliminada")
