from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin
from app.models.enums import EmailStatus


class Email(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "emails"

    message_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[EmailStatus] = mapped_column(
        SAEnum(EmailStatus, name="email_status"), nullable=False, default=EmailStatus.pending
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_stored_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    documents = relationship("Document", back_populates="email", lazy="raise")
