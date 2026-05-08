from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PrimaryKeyMixin, TimestampMixin


class Person(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "persons"

    name: Mapped[str] = mapped_column(Text, nullable=False)

    user = relationship("User", back_populates="person", uselist=False, lazy="raise")
    accounts = relationship("Account", back_populates="person", lazy="raise")
