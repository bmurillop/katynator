from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin, require_member
from app.db import get_db
from app.models.category_rule import CategoryRule
from app.models.enums import CategorySource, MatchType
from app.models.transaction import Transaction
from app.pipeline.rule_engine import apply_rules
from app.schemas.category_rule import CategoryRuleCreate, CategoryRuleOut, CategoryRuleUpdate
from app.schemas.common import MessageResponse

router = APIRouter()


def _apply_memo_filter(q, match_type: str, memo_pattern: str):
    """Add a description_normalized filter matching the given match_type."""
    p = memo_pattern.lower()
    if match_type == "contains":
        return q.where(Transaction.description_normalized.ilike(f"%{p}%"))
    if match_type == "starts_with":
        return q.where(Transaction.description_normalized.ilike(f"{p}%"))
    if match_type == "exact":
        return q.where(Transaction.description_normalized == p)
    if match_type == "regex":
        return q.where(Transaction.description_normalized.op("~*")(memo_pattern))
    return q


@router.get("/category-rules/preview", dependencies=[Depends(require_member)])
async def preview_rule(
    memo_pattern: Optional[str] = Query(None),
    match_type: str = Query("contains"),
    entity_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Count transactions that would be matched by a prospective rule."""
    q = select(func.count()).select_from(Transaction)
    if entity_id:
        q = q.where(Transaction.merchant_entity_id == entity_id)
    if memo_pattern:
        q = _apply_memo_filter(q, match_type, memo_pattern)
    count = (await db.execute(q)).scalar() or 0
    return {"count": count}


@router.post("/category-rules/reapply", dependencies=[Depends(require_member)])
async def reapply_rules(db: AsyncSession = Depends(get_db)):
    """Re-run all rules against every transaction not manually categorized by the user."""
    rules = (
        await db.execute(select(CategoryRule).order_by(CategoryRule.priority.desc()))
    ).scalars().all()

    q = select(Transaction).where(
        or_(
            Transaction.category_source.is_(None),
            Transaction.category_source == CategorySource.ai_suggested,
            Transaction.category_source == CategorySource.rule,
        )
    )
    txns = (await db.execute(q)).scalars().all()

    applied = 0
    for txn in txns:
        cat_id, cat_source, is_transfer = apply_rules(rules, txn.merchant_entity_id, txn.description_normalized)
        if is_transfer and not txn.is_transfer:
            txn.is_transfer = True
            txn.category_id = None
            txn.category_source = None
            txn.needs_review = False
            applied += 1
        elif cat_id and txn.category_id != cat_id:
            txn.category_id = cat_id
            txn.category_source = cat_source
            txn.is_transfer = False
            txn.needs_review = False
            applied += 1

    await db.commit()
    return {"applied": applied, "checked": len(txns)}


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
        sets_transfer=body.sets_transfer,
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


@router.post("/category-rules/{rule_id}/apply", dependencies=[Depends(require_member)])
async def apply_rule(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    """Apply a single rule to all matching transactions that haven't been manually categorized."""
    rule = (
        await db.execute(select(CategoryRule).where(CategoryRule.id == rule_id))
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    q = select(Transaction).where(
        or_(
            Transaction.category_source.is_(None),
            Transaction.category_source == CategorySource.ai_suggested,
            Transaction.category_source == CategorySource.rule,
        )
    )
    if rule.entity_id:
        q = q.where(Transaction.merchant_entity_id == rule.entity_id)
    if rule.memo_pattern and rule.match_type != MatchType.any:
        q = _apply_memo_filter(q, rule.match_type.value, rule.memo_pattern)

    txns = (await db.execute(q)).scalars().all()
    applied = 0
    for txn in txns:
        if rule.sets_transfer:
            if not txn.is_transfer:
                txn.is_transfer = True
                txn.category_id = None
                txn.category_source = None
                txn.needs_review = False
                applied += 1
        else:
            if txn.category_id != rule.category_id:
                txn.category_id = rule.category_id
                txn.category_source = CategorySource.rule
                txn.is_transfer = False
                txn.needs_review = False
                applied += 1

    await db.commit()
    return {"applied": applied}


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
