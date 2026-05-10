from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin
from app.models.enums import MatchType, RuleSource


class EntityRule(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "entity_rules"
    __table_args__ = (
        UniqueConstraint("memo_pattern", "match_type", name="uq_entity_rules_pattern_type"),
    )

    memo_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    match_type: Mapped[MatchType] = mapped_column(
        SAEnum(MatchType, name="match_type", create_constraint=False), nullable=False
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    source: Mapped[RuleSource] = mapped_column(
        SAEnum(RuleSource, name="rule_source", create_constraint=False), nullable=False
    )

    entity = relationship("Entity", lazy="raise")
