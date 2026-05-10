from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.models.enums import MatchType, RuleSource


class CategoryRuleOut(BaseModel):
    id: UUID
    entity_id: Optional[UUID]
    memo_pattern: Optional[str]
    match_type: MatchType
    category_id: Optional[UUID]
    sets_transfer: bool
    priority: int
    source: RuleSource
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryRuleCreate(BaseModel):
    entity_id: Optional[UUID] = None
    memo_pattern: Optional[str] = None
    match_type: MatchType = MatchType.any
    category_id: Optional[UUID] = None
    sets_transfer: bool = False
    priority: int = 50
    source: RuleSource = RuleSource.user_confirmed

    @model_validator(mode="after")
    def validate_rule(self) -> "CategoryRuleCreate":
        if self.entity_id is None and self.memo_pattern is None:
            raise ValueError("entity_id o memo_pattern deben estar presentes")
        if self.category_id is None and not self.sets_transfer:
            raise ValueError("category_id o sets_transfer=true deben estar presentes")
        return self


class CategoryRuleUpdate(BaseModel):
    entity_id: Optional[UUID] = None
    memo_pattern: Optional[str] = None
    match_type: Optional[MatchType] = None
    category_id: Optional[UUID] = None
    sets_transfer: Optional[bool] = None
    priority: Optional[int] = None
