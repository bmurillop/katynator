"""User management API.

GET  /api/users/me           — own profile (any authenticated user)
GET  /api/users              — list all users (admin)
GET  /api/users/{id}         — get user by id (admin)
POST /api/users              — create user, auto-creates Person if none given (admin)
PATCH /api/users/{id}        — update role or person link (admin)
POST /api/users/{id}/reset-password — set temp password, force change on next login (admin)

Guards:
  - Admin cannot demote their own role (would lock them out).
  - person_id must refer to a Person not already linked to another User.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_admin, require_member
from app.db import get_db
from app.models.enums import UserRole
from app.models.person import Person
from app.models.user import User
from app.schemas.user import AdminResetPassword, UserCreate, UserOut, UserUpdate

router = APIRouter()
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/users/me", response_model=UserOut, dependencies=[Depends(require_member)])
async def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
    return [UserOut.model_validate(r) for r in rows]


@router.get("/users/{user_id}", response_model=UserOut, dependencies=[Depends(require_admin)])
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UserOut.model_validate(row)


@router.post("/users", response_model=UserOut, status_code=201, dependencies=[Depends(require_admin)])
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = (
        await db.execute(select(User).where(User.email == body.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")

    person_id = body.person_id
    if person_id:
        # Verify the Person exists and isn't already linked to a User
        person = (await db.execute(select(Person).where(Person.id == person_id))).scalar_one_or_none()
        if person is None:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
        taken = (
            await db.execute(select(User.id).where(User.person_id == person_id))
        ).scalar_one_or_none()
        if taken:
            raise HTTPException(status_code=409, detail="Esa persona ya está vinculada a otro usuario")
    else:
        # Auto-create a Person from the email username
        username = body.email.split("@")[0].replace(".", " ").title()
        person = Person(name=username)
        db.add(person)
        await db.flush()
        person_id = person.id

    user = User(
        email=body.email,
        password_hash=_pwd_ctx.hash(body.password),
        role=body.role,
        person_id=person_id,
        must_change_password=True,
    )
    db.add(user)
    await db.flush()
    return UserOut.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserOut, dependencies=[Depends(require_admin)])
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    updates = body.model_dump(exclude_unset=True)

    if "role" in updates and updates["role"] != UserRole.admin and row.id == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="No puedes quitarte el rol de administrador a ti mismo",
        )

    if "person_id" in updates and updates["person_id"] is not None:
        pid = updates["person_id"]
        person = (await db.execute(select(Person).where(Person.id == pid))).scalar_one_or_none()
        if person is None:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
        taken = (
            await db.execute(
                select(User.id).where(User.person_id == pid, User.id != user_id)
            )
        ).scalar_one_or_none()
        if taken:
            raise HTTPException(status_code=409, detail="Esa persona ya está vinculada a otro usuario")

    for field, value in updates.items():
        setattr(row, field, value)

    await db.flush()
    return UserOut.model_validate(row)


@router.post(
    "/users/{user_id}/reset-password",
    response_model=dict,
    dependencies=[Depends(require_admin)],
)
async def reset_password(
    user_id: UUID,
    body: AdminResetPassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set a temporary password for any user. Forces password change on next login."""
    row = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    row.password_hash = _pwd_ctx.hash(body.new_password)
    row.must_change_password = True
    row.token_version += 1  # invalidate all existing sessions
    await db.flush()
    return {"message": "Contraseña restablecida. El usuario deberá cambiarla al iniciar sesión."}
