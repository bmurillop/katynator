from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import EntityType, PatternSource


class EntityPatternOut(BaseModel):
    id: UUID
    entity_id: UUID
    pattern: str
    normalized: str
    source: PatternSource
    created_at: datetime

    model_config = {"from_attributes": True}


class EntityOut(BaseModel):
    id: UUID
    canonical_name: str
    display_name: Optional[str]
    type: EntityType
    confirmed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EntityDetail(EntityOut):
    patterns: list[EntityPatternOut] = []


class EntityCreate(BaseModel):
    canonical_name: str
    display_name: Optional[str] = None
    type: EntityType
    confirmed: bool = True


class EntityUpdate(BaseModel):
    canonical_name: Optional[str] = None
    display_name: Optional[str] = None
    type: Optional[EntityType] = None
    confirmed: Optional[bool] = None


class PatternCreate(BaseModel):
    pattern: str
    source: PatternSource = PatternSource.user_added


class EntityListResponse(BaseModel):
    items: list[EntityOut]
    total: int
    page: int
    page_size: int
