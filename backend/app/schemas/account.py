from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AccountType, Currency


class AccountOut(BaseModel):
    id: UUID
    person_id: UUID
    bank_entity_id: Optional[UUID]
    issuer_entity_id: Optional[UUID]
    account_type: AccountType
    currency: Currency
    nickname: Optional[str]
    account_number_hint: Optional[str]
    last_known_balance: Optional[Decimal]
    balance_as_of: Optional[date]
    confirmed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountUpdate(BaseModel):
    nickname: Optional[str] = None
    account_type: Optional[AccountType] = None
    confirmed: Optional[bool] = None
    bank_entity_id: Optional[UUID] = None
    issuer_entity_id: Optional[UUID] = None


class AccountListResponse(BaseModel):
    items: list[AccountOut]
    total: int
    page: int
    page_size: int
