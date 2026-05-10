"""Transaction API.

Route ordering matters: /summary must be declared before /{transaction_id}
so FastAPI doesn't try to cast "summary" as a UUID.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

import logging

from app.auth.deps import require_admin, require_member
from app.db import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.entity import Entity
from app.models.enums import CategorySource, Currency, TransactionDirection
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)
from app.schemas.transaction import (
    TransactionListResponse,
    TransactionMonthlyItem,
    TransactionMonthlyResponse,
    TransactionOut,
    TransactionSummaryItem,
    TransactionSummaryResponse,
    TransactionUpdate,
)

router = APIRouter()


@router.get(
    "/transactions/summary",
    response_model=TransactionSummaryResponse,
    dependencies=[Depends(require_member)],
)
async def transaction_summary(
    person_id: UUID | None = None,
    account_id: UUID | None = None,
    currency: Currency | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Aggregate debit/credit totals per currency.  Never mixes currencies."""
    q = (
        select(
            Transaction.currency,
            Transaction.direction,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .where(Transaction.is_transfer.is_(False))
        .group_by(Transaction.currency, Transaction.direction)
    )

    if account_id:
        q = q.where(Transaction.account_id == account_id)
    elif person_id:
        # Join via account to filter by person
        q = q.join(Account, Transaction.account_id == Account.id).where(
            Account.person_id == person_id
        )
    if currency:
        q = q.where(Transaction.currency == currency)
    if date_from:
        q = q.where(Transaction.date >= date_from)
    if date_to:
        q = q.where(Transaction.date <= date_to)

    rows = (await db.execute(q)).all()
    summaries = [
        TransactionSummaryItem(
            currency=r.currency,
            direction=r.direction,
            total=r.total,
            count=r.count,
        )
        for r in rows
    ]
    return TransactionSummaryResponse(summaries=summaries)


@router.get(
    "/transactions/summary/monthly",
    response_model=TransactionMonthlyResponse,
    dependencies=[Depends(require_member)],
)
async def transaction_summary_monthly(
    person_id: UUID | None = None,
    account_id: UUID | None = None,
    currency: Currency | None = None,
    months: int = Query(6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
):
    """Month-bucketed debit/credit totals for chart data. Never mixes currencies."""
    today = date.today()
    total_m = today.year * 12 + today.month - (months - 1)
    start_year = (total_m - 1) // 12
    start_month = (total_m - 1) % 12 + 1
    start_date = date(start_year, start_month, 1)

    month_col = func.to_char(Transaction.date, "YYYY-MM")

    q = select(
        month_col.label("month"),
        Transaction.currency,
        Transaction.direction,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count"),
    ).where(Transaction.date >= start_date, Transaction.is_transfer.is_(False))

    if account_id:
        q = q.where(Transaction.account_id == account_id)
    elif person_id:
        q = q.join(Account, Transaction.account_id == Account.id).where(
            Account.person_id == person_id
        )
    if currency:
        q = q.where(Transaction.currency == currency)

    q = q.group_by(month_col, Transaction.currency, Transaction.direction).order_by(month_col)

    rows = (await db.execute(q)).all()
    return TransactionMonthlyResponse(
        items=[
            TransactionMonthlyItem(
                month=r.month,
                currency=r.currency,
                direction=r.direction,
                total=r.total,
                count=r.count,
            )
            for r in rows
        ]
    )


@router.get("/transactions/summary/by-category", dependencies=[Depends(require_member)])
async def transaction_summary_by_category(
    person_id: UUID | None = None,
    account_id: UUID | None = None,
    currency: Currency | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Debit totals grouped by top-level category (rolls up subcategories to parent)."""
    parent_cat = aliased(Category)
    q = (
        select(
            func.coalesce(parent_cat.id, Category.id).label("category_id"),
            func.coalesce(parent_cat.name, Category.name).label("category_name"),
            func.coalesce(parent_cat.color, Category.color).label("category_color"),
            Transaction.currency,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .outerjoin(parent_cat, Category.parent_id == parent_cat.id)
        .where(
            Transaction.direction == TransactionDirection.debit,
            Transaction.is_transfer.is_(False),
            Transaction.category_id.isnot(None),
        )
        .group_by(
            func.coalesce(parent_cat.id, Category.id),
            func.coalesce(parent_cat.name, Category.name),
            func.coalesce(parent_cat.color, Category.color),
            Transaction.currency,
        )
        .order_by(func.sum(Transaction.amount).desc())
    )

    if account_id:
        q = q.where(Transaction.account_id == account_id)
    elif person_id:
        q = q.join(Account, Transaction.account_id == Account.id).where(
            Account.person_id == person_id
        )
    if currency:
        q = q.where(Transaction.currency == currency)
    if date_from:
        q = q.where(Transaction.date >= date_from)
    if date_to:
        q = q.where(Transaction.date <= date_to)

    rows = (await db.execute(q)).all()
    return {
        "items": [
            {
                "category_id": str(r.category_id),
                "category_name": r.category_name,
                "category_color": r.category_color,
                "currency": r.currency,
                "total": float(r.total),
                "count": r.count,
            }
            for r in rows
        ]
    }


@router.post("/transactions/suggest-categories", dependencies=[Depends(require_member)])
async def suggest_categories_ai(db: AsyncSession = Depends(get_db)):
    """Ask the active AI provider to suggest categories for all uncategorized, non-transfer transactions."""
    from app.ai.factory import get_active_provider

    provider = await get_active_provider(db)

    categories = (await db.execute(select(Category))).scalars().all()
    cat_name_to_id = {c.name: c.id for c in categories}
    cat_names = list(cat_name_to_id.keys())

    if not cat_names:
        return {"suggested": 0, "checked": 0}

    txns = (
        await db.execute(
            select(Transaction).where(
                Transaction.category_id.is_(None),
                Transaction.is_transfer.is_(False),
            )
        )
    ).scalars().all()

    suggested = 0
    for txn in txns:
        try:
            name = await provider.suggest_category(txn.description_raw, cat_names)
            if name and name in cat_name_to_id:
                txn.category_id = cat_name_to_id[name]
                txn.category_source = CategorySource.ai_suggested
                txn.needs_review = True
                suggested += 1
        except Exception:
            logger.warning("AI suggestion failed for transaction %s", txn.id, exc_info=True)

    await db.commit()
    return {"suggested": suggested, "checked": len(txns)}


@router.post("/transactions/suggest-entities", dependencies=[Depends(require_member)])
async def suggest_entities_ai(db: AsyncSession = Depends(get_db)):
    """Ask the active AI provider to suggest an entity for transactions with none resolved."""
    from app.ai.factory import get_active_provider

    provider = await get_active_provider(db)

    entities = (await db.execute(select(Entity))).scalars().all()
    entity_name_to_id = {e.canonical_name: e.id for e in entities}
    entity_names = list(entity_name_to_id.keys())

    if not entity_names:
        return {"suggested": 0, "checked": 0}

    txns = (
        await db.execute(
            select(Transaction).where(Transaction.merchant_entity_id.is_(None))
        )
    ).scalars().all()

    suggested = 0
    for txn in txns:
        try:
            name = await provider.suggest_entity_match(txn.description_raw, entity_names)
            if name and name in entity_name_to_id:
                txn.merchant_entity_id = entity_name_to_id[name]
                suggested += 1
        except Exception:
            logger.warning("AI entity suggestion failed for transaction %s", txn.id, exc_info=True)

    await db.commit()
    return {"suggested": suggested, "checked": len(txns)}


@router.get("/transactions", response_model=TransactionListResponse, dependencies=[Depends(require_member)])
async def list_transactions(
    person_id: UUID | None = None,
    account_id: UUID | None = None,
    currency: Currency | None = None,
    direction: TransactionDirection | None = None,
    category_id: UUID | None = None,
    needs_review: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Transaction)

    if account_id:
        q = q.where(Transaction.account_id == account_id)
    elif person_id:
        q = q.join(Account, Transaction.account_id == Account.id).where(
            Account.person_id == person_id
        )
    if currency:
        q = q.where(Transaction.currency == currency)
    if direction:
        q = q.where(Transaction.direction == direction)
    if category_id:
        q = q.where(Transaction.category_id == category_id)
    if needs_review is not None:
        q = q.where(Transaction.needs_review == needs_review)
    if date_from:
        q = q.where(Transaction.date >= date_from)
    if date_to:
        q = q.where(Transaction.date <= date_to)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (
        await db.execute(
            q.order_by(Transaction.date.desc(), Transaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return TransactionListResponse(
        items=[TransactionOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionOut, dependencies=[Depends(require_member)])
async def get_transaction(transaction_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return TransactionOut.model_validate(row)


@router.patch("/transactions/{transaction_id}", response_model=TransactionOut, dependencies=[Depends(require_member)])
async def update_transaction(
    transaction_id: UUID,
    body: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(row, field, value)

    # When a user manually sets a category, upgrade source to user_set
    if "category_id" in updates and "category_source" not in updates:
        row.category_source = CategorySource.user_set

    await db.commit()
    return TransactionOut.model_validate(row)
