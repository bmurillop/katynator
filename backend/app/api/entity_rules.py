"""Entity rules API.

Rules map memo patterns → entities. They run in the pipeline after exact/fuzzy
pattern matching and before the AI suggestion step, making entity identification
deterministic for known payees without AI calls.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin, require_member
from app.db import get_db
from app.models.entity_rule import EntityRule
from app.models.enums import MatchType
from app.models.transaction import Transaction
from app.pipeline.dedup import normalize_description
from app.schemas.common import MessageResponse
from app.schemas.entity_rule import EntityRuleCreate, EntityRuleOut, EntityRuleUpdate

router = APIRouter()


def _apply_pattern_filter(q, match_type: str, memo_pattern: str):
    """Filter transactions by description_normalized using the given match type."""
    p = memo_pattern.lower()
    if match_type == MatchType.contains:
        return q.where(Transaction.description_normalized.ilike(f"%{p}%"))
    if match_type == MatchType.starts_with:
        return q.where(Transaction.description_normalized.ilike(f"{p}%"))
    if match_type == MatchType.exact:
        return q.where(Transaction.description_normalized == p)
    if match_type == MatchType.regex:
        return q.where(Transaction.description_normalized.op("~*")(memo_pattern))
    return q


@router.get("/entity-rules/preview", dependencies=[Depends(require_member)])
async def preview_entity_rule(
    memo_pattern: str = Query(...),
    match_type: str = Query("contains"),
    db: AsyncSession = Depends(get_db),
):
    """Count transactions that would be matched by a prospective entity rule."""
    q = select(func.count()).select_from(Transaction)
    q = _apply_pattern_filter(q, match_type, memo_pattern)
    count = (await db.execute(q)).scalar() or 0
    return {"count": count}


@router.post("/entity-rules/reapply", dependencies=[Depends(require_member)])
async def reapply_entity_rules(db: AsyncSession = Depends(get_db)):
    """Re-run all entity rules against transactions with no resolved entity."""
    rules = (
        await db.execute(
            select(EntityRule).order_by(EntityRule.priority.desc())
        )
    ).scalars().all()

    txns = (
        await db.execute(
            select(Transaction).where(Transaction.merchant_entity_id.is_(None))
        )
    ).scalars().all()

    applied = 0
    for txn in txns:
        for rule in rules:
            if _matches(rule, txn.description_normalized or ""):
                txn.merchant_entity_id = rule.entity_id
                applied += 1
                break

    await db.commit()
    return {"applied": applied, "checked": len(txns)}


@router.get("/entity-rules", response_model=list[EntityRuleOut], dependencies=[Depends(require_member)])
async def list_entity_rules(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(select(EntityRule).order_by(EntityRule.priority.desc()))
    ).scalars().all()
    return [EntityRuleOut.model_validate(r) for r in rows]


@router.post("/entity-rules", response_model=EntityRuleOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_entity_rule(body: EntityRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = EntityRule(
        memo_pattern=body.memo_pattern,
        match_type=body.match_type,
        entity_id=body.entity_id,
        priority=body.priority,
        source=body.source,
    )
    db.add(rule)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una regla con ese patrón y tipo de match")
    return EntityRuleOut.model_validate(rule)


@router.post("/entity-rules/{rule_id}/apply", dependencies=[Depends(require_member)])
async def apply_entity_rule(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    """Apply a single entity rule to all transactions with no resolved entity."""
    rule = (
        await db.execute(select(EntityRule).where(EntityRule.id == rule_id))
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    txns = (
        await db.execute(
            select(Transaction).where(Transaction.merchant_entity_id.is_(None))
        )
    ).scalars().all()

    applied = 0
    for txn in txns:
        if _matches(rule, txn.description_normalized or ""):
            txn.merchant_entity_id = rule.entity_id
            applied += 1

    await db.commit()
    return {"applied": applied}


@router.patch("/entity-rules/{rule_id}", response_model=EntityRuleOut, dependencies=[Depends(require_admin)])
async def update_entity_rule(
    rule_id: UUID, body: EntityRuleUpdate, db: AsyncSession = Depends(get_db)
):
    row = (
        await db.execute(select(EntityRule).where(EntityRule.id == rule_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)

    await db.commit()
    return EntityRuleOut.model_validate(row)


@router.delete("/entity-rules/{rule_id}", response_model=MessageResponse, dependencies=[Depends(require_admin)])
async def delete_entity_rule(rule_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(select(EntityRule).where(EntityRule.id == rule_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    await db.delete(row)
    await db.commit()
    return MessageResponse(message="Regla eliminada")


def _matches(rule: EntityRule, description_normalized: str) -> bool:
    """Test whether a description matches an entity rule."""
    p = (rule.memo_pattern or "").lower()
    d = description_normalized.lower()
    if rule.match_type == MatchType.contains:
        return p in d
    if rule.match_type == MatchType.starts_with:
        return d.startswith(p)
    if rule.match_type == MatchType.exact:
        return d == p
    if rule.match_type == MatchType.regex:
        import re
        return bool(re.search(rule.memo_pattern or "", d, re.IGNORECASE))
    if rule.match_type == MatchType.any:
        return True
    return False
