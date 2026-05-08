from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin, require_member
from app.db import get_db
from app.models.account import Account
from app.models.enums import Currency
from app.schemas.account import AccountListResponse, AccountOut, AccountUpdate

router = APIRouter()


@router.get("/accounts", response_model=AccountListResponse, dependencies=[Depends(require_member)])
async def list_accounts(
    person_id: UUID | None = None,
    currency: Currency | None = None,
    confirmed: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Account)
    if person_id:
        q = q.where(Account.person_id == person_id)
    if currency:
        q = q.where(Account.currency == currency)
    if confirmed is not None:
        q = q.where(Account.confirmed == confirmed)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (
        await db.execute(q.order_by(Account.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()

    return AccountListResponse(
        items=[AccountOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/accounts/{account_id}", response_model=AccountOut, dependencies=[Depends(require_member)])
async def get_account(account_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Account).where(Account.id == account_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return AccountOut.model_validate(row)


@router.patch("/accounts/{account_id}", response_model=AccountOut, dependencies=[Depends(require_admin)])
async def update_account(
    account_id: UUID,
    body: AccountUpdate,
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(select(Account).where(Account.id == account_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)

    await db.flush()
    return AccountOut.model_validate(row)
