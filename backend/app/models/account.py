import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, Enum as SAEnum, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin
from app.models.enums import AccountType, Currency


class Account(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint(
            "person_id", "account_number_hint", "bank_entity_id",
            name="uq_accounts_person_hint_bank",
        ),
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("persons.id"), nullable=False
    )
    bank_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True
    )
    issuer_entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True
    )
    account_type: Mapped[AccountType] = mapped_column(
        SAEnum(AccountType, name="account_type"), nullable=False
    )
    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency"), nullable=False
    )
    nickname: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    account_number_hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_known_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    balance_as_of: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    person = relationship("Person", back_populates="accounts", lazy="raise")
    bank_entity = relationship("Entity", foreign_keys=[bank_entity_id], lazy="raise")
    issuer_entity = relationship("Entity", foreign_keys=[issuer_entity_id], lazy="raise")
    transactions = relationship("Transaction", back_populates="account", lazy="raise")
