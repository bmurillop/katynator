import uuid
from typing import Optional

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin
from app.models.enums import UnresolvedEntityStatus


class UnresolvedEntityName(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "unresolved_entity_names"

    raw_name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    suggested_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id", ondelete="SET NULL"), nullable=True
    )
    suggestion_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[UnresolvedEntityStatus] = mapped_column(
        SAEnum(UnresolvedEntityStatus, name="unresolved_entity_status"),
        nullable=False,
        default=UnresolvedEntityStatus.pending,
    )
    resolved_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id", ondelete="SET NULL"), nullable=True
    )

    document = relationship("Document", lazy="raise", foreign_keys=[document_id])
    suggested_entity = relationship("Entity", lazy="raise", foreign_keys=[suggested_entity_id])
    resolved_entity = relationship("Entity", lazy="raise", foreign_keys=[resolved_entity_id])
