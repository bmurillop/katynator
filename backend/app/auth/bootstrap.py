import logging
import uuid

from passlib.context import CryptContext
from sqlalchemy import func, select

from app.config import settings
from app.db import AsyncSessionLocal
from app.models.category import Category
from app.models.enums import UserRole
from app.models.user import User

logger = logging.getLogger(__name__)

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

_DEFAULT_CATEGORIES: list[tuple[str, str]] = [
    ("Food & Dining",  "#ef4444"),
    ("Groceries",      "#22c55e"),
    ("Transport",      "#3b82f6"),
    ("Fuel",           "#f97316"),
    ("Utilities",      "#8b5cf6"),
    ("Entertainment",  "#ec4899"),
    ("Health",         "#14b8a6"),
    ("Education",      "#0ea5e9"),
    ("Shopping",       "#f59e0b"),
    ("Travel",         "#6366f1"),
    ("Income",         "#10b981"),
    ("Transfers",      "#64748b"),
    ("Fees & Charges", "#dc2626"),
    ("Other",          "#9ca3af"),
]


async def bootstrap_admin() -> None:
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
        if count > 0:
            return

        if not settings.admin_email or not settings.admin_password:
            logger.warning(
                "No users exist and ADMIN_EMAIL/ADMIN_PASSWORD are not set — "
                "the app will be inaccessible until an admin is created manually."
            )
            return

        db.add(User(
            id=uuid.uuid4(),
            email=settings.admin_email,
            password_hash=_pwd_ctx.hash(settings.admin_password),
            role=UserRole.admin,
            must_change_password=False,
            token_version=0,
        ))
        await db.commit()
        logger.info("Admin user created: %s", settings.admin_email)


async def seed_categories() -> None:
    async with AsyncSessionLocal() as db:
        count = (await db.execute(select(func.count()).select_from(Category))).scalar_one()
        if count > 0:
            return

        for name, color in _DEFAULT_CATEGORIES:
            db.add(Category(id=uuid.uuid4(), name=name, color=color, is_system=True))
        await db.commit()
        logger.info("Seeded %d default categories.", len(_DEFAULT_CATEGORIES))
