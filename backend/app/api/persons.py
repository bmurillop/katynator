from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_member
from app.db import get_db
from app.models.person import Person
from app.schemas.person import PersonOut

router = APIRouter()


@router.get("/persons", response_model=list[PersonOut], dependencies=[Depends(require_member)])
async def list_persons(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Person).order_by(Person.name))).scalars().all()
    return [PersonOut.model_validate(r) for r in rows]
