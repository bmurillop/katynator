import uuid

from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TransactionDocument(Base):
    __tablename__ = "transaction_documents"
    __table_args__ = (
        PrimaryKeyConstraint("transaction_id", "document_id", name="pk_transaction_documents"),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )

    transaction = relationship("Transaction", back_populates="transaction_documents", lazy="raise")
    document = relationship("Document", back_populates="transaction_documents", lazy="raise")
