import uuid

from sqlalchemy import Enum as SAEnum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin
from app.models.enums import PatternSource


class EntityPattern(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "entity_patterns"
    __table_args__ = (
        UniqueConstraint("entity_id", "normalized", name="uq_entity_patterns_entity_normalized"),
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False
    )
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    normalized: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[PatternSource] = mapped_column(
        SAEnum(PatternSource, name="pattern_source"), nullable=False
    )

    entity = relationship("Entity", back_populates="patterns", lazy="raise")
