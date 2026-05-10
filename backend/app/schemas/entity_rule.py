from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.models.enums import MatchType, RuleSource


class EntityRuleOut(BaseModel):
    id: UUID
    memo_pattern: str
    match_type: MatchType
    entity_id: UUID
    priority: int
    source: RuleSource

    model_config = {"from_attributes": True}


class EntityRuleCreate(BaseModel):
    memo_pattern: str
    match_type: MatchType = MatchType.contains
    entity_id: UUID
    priority: int = 50
    source: RuleSource = RuleSource.user_confirmed


class EntityRuleUpdate(BaseModel):
    memo_pattern: str | None = None
    match_type: MatchType | None = None
    entity_id: UUID | None = None
    priority: int | None = None
