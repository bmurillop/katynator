from __future__ import annotations

import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, PrimaryKeyMixin


class Category(Base, PrimaryKeyMixin):
    __tablename__ = "categories"
    __table_args__ = (
        # Per-level uniqueness — "Misc" may appear under multiple parents.
        Index("uq_categories_name_toplevel", "name", unique=True,
              postgresql_where=sa.text("parent_id IS NULL")),
        Index("uq_categories_name_child", "name", "parent_id", unique=True,
              postgresql_where=sa.text("parent_id IS NOT NULL")),
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
    )
