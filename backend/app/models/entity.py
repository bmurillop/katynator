from typing import Optional

from sqlalchemy import Boolean, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin
from app.models.enums import EntityType


class Entity(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "entities"

    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[EntityType] = mapped_column(
        SAEnum(EntityType, name="entity_type"), nullable=False
    )
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    patterns = relationship("EntityPattern", back_populates="entity", lazy="raise")
