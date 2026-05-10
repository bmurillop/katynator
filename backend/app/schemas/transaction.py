from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import CategorySource, Currency, TransactionDirection


class TransactionOut(BaseModel):
    id: UUID
    account_id: UUID
    date: date
    posted_date: Optional[date]
    description_raw: str
    description_normalized: str
    merchant_entity_id: Optional[UUID]
    amount: Decimal
    direction: TransactionDirection
    currency: Currency  # always present — never omit
    category_id: Optional[UUID]
    category_source: Optional[CategorySource]
    needs_review: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionUpdate(BaseModel):
    category_id: Optional[UUID] = None
    category_source: Optional[CategorySource] = None
    merchant_entity_id: Optional[UUID] = None
    needs_review: Optional[bool] = None


class TransactionSummaryItem(BaseModel):
    currency: Currency
    direction: TransactionDirection
    total: Decimal
    count: int


class TransactionSummaryResponse(BaseModel):
    summaries: list[TransactionSummaryItem]


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int


class TransactionMonthlyItem(BaseModel):
    month: str  # "YYYY-MM"
    currency: Currency
    direction: TransactionDirection
    total: Decimal
    count: int


class TransactionMonthlyResponse(BaseModel):
    items: list[TransactionMonthlyItem]
