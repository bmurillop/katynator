from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin, require_member
from app.db import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter()


@router.get("/categories", response_model=list[CategoryOut], dependencies=[Depends(require_member)])
async def list_categories(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Category).order_by(Category.name))).scalars().all()
    return [CategoryOut.model_validate(r) for r in rows]


@router.post("/categories", response_model=CategoryOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)):
    existing = (
        await db.execute(select(Category).where(Category.name == body.name))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre")

    cat = Category(name=body.name, color=body.color, icon=body.icon, is_system=False)
    db.add(cat)
    await db.flush()
    return CategoryOut.model_validate(cat)


@router.patch("/categories/{category_id}", response_model=CategoryOut, dependencies=[Depends(require_admin)])
async def update_category(
    category_id: UUID, body: CategoryUpdate, db: AsyncSession = Depends(get_db)
):
    row = (await db.execute(select(Category).where(Category.id == category_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    if row.is_system:
        raise HTTPException(status_code=403, detail="Las categorías del sistema no se pueden modificar")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)

    await db.flush()
    return CategoryOut.model_validate(row)
