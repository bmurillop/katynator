from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import EntityType, UnresolvedEntityStatus


class UnresolvedEntityOut(BaseModel):
    id: UUID
    raw_name: str
    normalized: str
    document_id: Optional[UUID]
    suggested_entity_id: Optional[UUID]
    suggestion_confidence: Optional[float]
    status: UnresolvedEntityStatus
    resolved_entity_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class ResolveRequest(BaseModel):
    entity_id: UUID


class CreateEntityRequest(BaseModel):
    canonical_name: str
    display_name: Optional[str] = None
    type: EntityType


class UnresolvedListResponse(BaseModel):
    items: list[UnresolvedEntityOut]
    total: int
    page: int
    page_size: int
