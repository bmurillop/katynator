import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin
from app.models.enums import CategorySource, Currency, TransactionDirection


class Transaction(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("account_id", "dedup_key", name="uq_transactions_account_dedup"),
        Index("ix_transactions_account_date", "account_id", "date"),
        Index("ix_transactions_category_date", "category_id", "date"),
        Index("ix_transactions_merchant", "merchant_entity_id"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    posted_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    description_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    merchant_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    direction: Mapped[TransactionDirection] = mapped_column(
        SAEnum(TransactionDirection, name="transaction_direction"), nullable=False
    )
    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency"), nullable=False
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    category_source: Mapped[Optional[CategorySource]] = mapped_column(
        SAEnum(CategorySource, name="category_source"), nullable=True
    )
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    account = relationship("Account", back_populates="transactions", lazy="raise")
    merchant_entity = relationship("Entity", lazy="raise")
    category = relationship("Category", lazy="raise")
    transaction_documents = relationship(
        "TransactionDocument", back_populates="transaction", lazy="raise"
    )
