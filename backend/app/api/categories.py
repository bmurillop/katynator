from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin, require_member
from app.db import get_db
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter()


@router.get("/categories", response_model=list[CategoryOut], dependencies=[Depends(require_member)])
async def list_categories(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Category).order_by(Category.name))).scalars().all()
    return [CategoryOut.model_validate(r) for r in rows]


@router.post("/categories", response_model=CategoryOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)):
    if body.parent_id is not None:
        parent = (await db.get(Category, body.parent_id))
        if parent is None:
            raise HTTPException(status_code=404, detail="Categoría padre no encontrada")
        if parent.parent_id is not None:
            raise HTTPException(status_code=400, detail="Solo se admite un nivel de subcategorías")

        # Check name uniqueness within parent
        conflict = (await db.execute(
            select(Category).where(Category.name == body.name, Category.parent_id == body.parent_id)
        )).scalar_one_or_none()
        if conflict:
            raise HTTPException(status_code=409, detail="Ya existe una subcategoría con ese nombre")

        # First child → auto-create "Misc" sibling and migrate any existing transactions
        existing_children = (await db.execute(
            select(Category).where(Category.parent_id == body.parent_id)
        )).scalars().all()

        if not existing_children:
            misc = Category(
                name="Misc",
                color=parent.color,
                icon=None,
                is_system=False,
                parent_id=body.parent_id,
            )
            db.add(misc)
            await db.flush()
            await db.execute(
                update(Transaction)
                .where(Transaction.category_id == body.parent_id)
                .values(category_id=misc.id)
            )
    else:
        # Top-level uniqueness
        conflict = (await db.execute(
            select(Category).where(Category.name == body.name, Category.parent_id.is_(None))
        )).scalar_one_or_none()
        if conflict:
            raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre")

    cat = Category(
        name=body.name,
        color=body.color,
        icon=body.icon,
        is_system=False,
        parent_id=body.parent_id,
    )
    db.add(cat)
    await db.commit()
    return CategoryOut.model_validate(cat)


@router.patch("/categories/{category_id}", response_model=CategoryOut, dependencies=[Depends(require_admin)])
async def update_category(
    category_id: UUID, body: CategoryUpdate, db: AsyncSession = Depends(get_db)
):
    row = (await db.execute(select(Category).where(Category.id == category_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)

    await db.commit()
    return CategoryOut.model_validate(row)


@router.delete("/categories/{category_id}", status_code=204, dependencies=[Depends(require_admin)])
async def delete_category(category_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(Category).where(Category.id == category_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    # Collect children IDs so we can null transaction references before cascade delete
    child_ids = (await db.execute(
        select(Category.id).where(Category.parent_id == category_id)
    )).scalars().all()
    all_ids = [category_id, *child_ids]

    await db.execute(
        update(Transaction).where(Transaction.category_id.in_(all_ids)).values(category_id=None, category_source=None)
    )
    await db.execute(delete(Category).where(Category.id == category_id))
    await db.commit()
