from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import DocType, EmailStatus, ReconciliationStatus


class EmailSummary(BaseModel):
    id: UUID
    message_id: str
    received_at: datetime
    sender: Optional[str]
    subject: Optional[str]
    status: EmailStatus
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentSummary(BaseModel):
    id: UUID
    doc_type: DocType
    filename: Optional[str]
    reconciliation_status: Optional[ReconciliationStatus]
    derived_quality_score: Optional[float]
    processed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EmailDetail(EmailSummary):
    documents: list[DocumentSummary] = []


class EmailListResponse(BaseModel):
    items: list[EmailSummary]
    total: int
    page: int
    page_size: int
