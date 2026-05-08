import uuid
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin
from app.models.enums import MatchType, RuleSource


class CategoryRule(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "category_rules"
    __table_args__ = (
        UniqueConstraint("entity_id", "memo_pattern", "match_type", name="uq_category_rules"),
        CheckConstraint(
            "entity_id IS NOT NULL OR memo_pattern IS NOT NULL",
            name="ck_rule_has_entity_or_memo",
        ),
    )

    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True
    )
    memo_pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    match_type: Mapped[MatchType] = mapped_column(
        SAEnum(MatchType, name="match_type"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    source: Mapped[RuleSource] = mapped_column(
        SAEnum(RuleSource, name="rule_source"), nullable=False
    )

    entity = relationship("Entity", lazy="raise")
    category = relationship("Category", lazy="raise")
