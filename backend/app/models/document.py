import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin
from app.models.enums import DocType, ReconciliationStatus


class Document(Base, PrimaryKeyMixin):
    __tablename__ = "documents"

    email_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("emails.id"), nullable=False
    )
    doc_type: Mapped[DocType] = mapped_column(
        SAEnum(DocType, name="doc_type"), nullable=False
    )
    filename: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_raw_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    reconciliation_status: Mapped[Optional[ReconciliationStatus]] = mapped_column(
        SAEnum(ReconciliationStatus, name="reconciliation_status"), nullable=True
    )
    reconciliation_details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    derived_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    email = relationship("Email", back_populates="documents", lazy="raise")
    transaction_documents = relationship(
        "TransactionDocument", back_populates="document", lazy="raise"
    )
