"""Email ingestion & pipeline status API.

Endpoints:
  GET  /api/emails            — paginated list (newest first)
  GET  /api/emails/{id}       — detail with document list
  POST /api/emails/{id}/retry — re-queue a failed email
  POST /api/emails/poll       — trigger an immediate IMAP poll (admin)
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.deps import require_admin, require_member
from app.db import get_db
from app.models.document import Document
from app.models.email_model import Email
from app.models.enums import EmailStatus
from app.schemas.common import MessageResponse
from app.schemas.email import EmailDetail, EmailListResponse, EmailSummary

router = APIRouter()


@router.get("/emails", response_model=EmailListResponse, dependencies=[Depends(require_member)])
async def list_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: EmailStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Email)
    if status:
        q = q.where(Email.status == status)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()

    rows = (
        await db.execute(
            q.order_by(Email.received_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return EmailListResponse(
        items=[EmailSummary.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/emails/{email_id}", response_model=EmailDetail, dependencies=[Depends(require_member)])
async def get_email(email_id: UUID, db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(
            select(Email)
            .options(selectinload(Email.documents))
            .where(Email.id == email_id)
        )
    ).scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="Email no encontrado")

    return EmailDetail.model_validate(row)


@router.post(
    "/emails/{email_id}/retry",
    response_model=MessageResponse,
    dependencies=[Depends(require_admin)],
)
async def retry_email(
    email_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(select(Email).where(Email.id == email_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Email no encontrado")

    if row.status not in (EmailStatus.failed, EmailStatus.skipped):
        raise HTTPException(
            status_code=409,
            detail=f"No se puede reintentar un email con estado '{row.status.value}'",
        )

    row.status = EmailStatus.pending
    row.error_message = None
    await db.flush()

    background_tasks.add_task(_run_pipeline, email_id)
    return MessageResponse(message="Email en cola para reprocesar")


@router.post(
    "/emails/poll",
    response_model=MessageResponse,
    dependencies=[Depends(require_admin)],
)
async def trigger_poll(background_tasks: BackgroundTasks):
    """Manually trigger an IMAP poll cycle (runs in background)."""
    from app.worker import run_poll_cycle

    background_tasks.add_task(run_poll_cycle)
    return MessageResponse(message="Sondeo IMAP iniciado")


async def _run_pipeline(email_id: UUID) -> None:
    from app.ai.factory import get_active_provider
    from app.db import AsyncSessionLocal
    from app.pipeline.coordinator import process_email

    async with AsyncSessionLocal() as db:
        try:
            provider = await get_active_provider(db)
            await process_email(email_id, db, provider)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
