from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin, require_member
from app.db import get_db
from app.models.account import Account
from app.models.person import Person
from app.models.user import User
from app.schemas.person import PersonCreate, PersonOut, PersonUpdate

router = APIRouter()


@router.get("/persons", response_model=list[PersonOut], dependencies=[Depends(require_member)])
async def list_persons(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Person).order_by(Person.name))).scalars().all()
    return [PersonOut.model_validate(r) for r in rows]


@router.post("/persons", response_model=PersonOut, dependencies=[Depends(require_admin)])
async def create_person(body: PersonCreate, db: AsyncSession = Depends(get_db)):
    person = Person(id=uuid.uuid4(), name=body.name.strip())
    db.add(person)
    await db.commit()
    return PersonOut.model_validate(person)


@router.patch("/persons/{person_id}", response_model=PersonOut, dependencies=[Depends(require_admin)])
async def update_person(person_id: UUID, body: PersonUpdate, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Person).where(Person.id == person_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    row.name = body.name.strip()
    await db.commit()
    return PersonOut.model_validate(row)


@router.delete("/persons/{person_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_person(person_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Person).where(Person.id == person_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")

    accounts = (await db.execute(select(Account).where(Account.person_id == person_id))).scalars().all()
    linked_user = (await db.execute(select(User).where(User.person_id == person_id))).scalar_one_or_none()

    if accounts or linked_user:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "La persona tiene recursos asignados y no puede eliminarse",
                "accounts": [
                    {
                        "id": str(a.id),
                        "label": a.nickname or (f"···{a.account_number_hint}" if a.account_number_hint else a.account_type.value),
                        "currency": a.currency.value,
                    }
                    for a in accounts
                ],
                "users": (
                    [{"id": str(linked_user.id), "email": linked_user.email}]
                    if linked_user else []
                ),
            },
        )

    await db.delete(row)
    await db.commit()
