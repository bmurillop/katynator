"""In-process email worker.

`run_poll_cycle()` is called by APScheduler on every poll interval.
It polls IMAP for new emails, then processes each pending email through
the full pipeline.  All errors are caught per-email; one failure doesn't
block the rest.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.ai.factory import get_active_provider
from app.db import AsyncSessionLocal
from app.models.email_model import Email
from app.models.enums import EmailStatus
from app.pipeline.coordinator import process_email
from app.pipeline.imap_poller import poll_and_ingest

logger = logging.getLogger(__name__)


async def run_poll_cycle() -> None:
    """Poll IMAP then process all pending emails."""
    async with AsyncSessionLocal() as db:
        try:
            new_ids = await poll_and_ingest(db)
            await db.commit()
            if new_ids:
                logger.info("Ingested %d new email(s)", len(new_ids))
        except Exception as exc:
            await db.rollback()
            logger.error("IMAP poll failed: %s", exc, exc_info=True)

    await _process_pending()


async def _process_pending() -> None:
    """Process every Email with status=pending."""
    async with AsyncSessionLocal() as db:
        pending_ids = list(
            (
                await db.execute(
                    select(Email.id).where(Email.status == EmailStatus.pending)
                )
            ).scalars()
        )

    for email_id in pending_ids:
        async with AsyncSessionLocal() as db:
            try:
                ai_provider = await get_active_provider(db)
                await process_email(email_id, db, ai_provider)
                await db.commit()
            except Exception as exc:
                await db.rollback()
                logger.error(
                    "Unhandled error processing email %s: %s", email_id, exc, exc_info=True
                )
