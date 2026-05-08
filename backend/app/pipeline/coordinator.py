"""Pipeline coordinator.

`process_email` is the top-level entry point called by the worker.
It reads a stored raw email from disk, parses it, and runs every pipeline
step for each extracted document (PDF attachments and body text).

All step failures are caught here: the Email record is marked failed with
the step name and exception message stored in error_message.
"""
from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.models.document import Document
from app.models.email_model import Email
from app.models.enums import DocType, EmailStatus, ReconciliationStatus
from app.pipeline.email_parser import ParsedEmail, parse_raw_email
from app.pipeline.entity_resolver import resolve_entity
from app.pipeline.pdf_extractor import extract_pdf_text
from app.pipeline.quality_score import REVIEW_THRESHOLD, compute_quality_score
from app.pipeline.reconciler import reconcile
from app.pipeline.transaction_builder import (
    build_transactions,
    match_or_create_account,
    match_or_create_person,
)

logger = logging.getLogger(__name__)


async def process_email(
    email_id: UUID,
    db: AsyncSession,
    ai_provider: AIProvider,
) -> None:
    """Full pipeline for one email record.

    Reads raw_stored_path from the Email row, parses the file, and processes
    every extracted document. Marks the email processed or failed.
    """
    email: Email = (await db.execute(
        select(Email).where(Email.id == email_id)
    )).scalar_one()

    email.status = EmailStatus.processing
    await db.flush()

    try:
        if not email.raw_stored_path:
            raise RuntimeError("Email has no raw_stored_path — cannot process")

        raw_bytes = Path(email.raw_stored_path).read_bytes()
        parsed = parse_raw_email(raw_bytes)

        # Process plain-text / HTML body parts
        for body_text in parsed.body_texts:
            if body_text.strip():
                doc = Document(
                    email_id=email.id,
                    doc_type=DocType.plain_text,
                    filename=None,
                    extracted_text=body_text,
                )
                db.add(doc)
                await db.flush()
                await process_document(doc, db, ai_provider)

        # Process PDF attachments
        for filename, pdf_bytes in parsed.pdf_attachments:
            extracted_text = _extract_pdf_bytes(pdf_bytes, filename)
            doc = Document(
                email_id=email.id,
                doc_type=DocType.pdf,
                filename=filename,
                extracted_text=extracted_text or None,
            )
            db.add(doc)
            await db.flush()
            if extracted_text:
                await process_document(doc, db, ai_provider)
            else:
                logger.warning("PDF %r yielded no text — skipping AI parse", filename)

        email.status = EmailStatus.processed

    except Exception as exc:
        logger.error("Pipeline failed for email %s: %s", email_id, exc, exc_info=True)
        email.status = EmailStatus.failed
        email.error_message = f"{type(exc).__name__}: {exc}"

    await db.flush()


async def process_document(
    document: Document,
    db: AsyncSession,
    ai_provider: AIProvider,
) -> None:
    """Run all pipeline steps for a single Document.

    Stores results back onto the Document row. On failure, raises — the
    caller (process_email) handles the error and marks the email failed.
    """
    if not document.extracted_text:
        return

    # ── Step 1: AI parse ─────────────────────────────────────────────────────
    parse_result = await ai_provider.parse_financial_document(document.extracted_text)
    document.ai_raw_response = parse_result.model_dump(mode="json")

    # ── Step 2: Reconcile ────────────────────────────────────────────────────
    recon = reconcile(parse_result)
    document.reconciliation_status = recon.status
    document.reconciliation_details = recon.details

    # ── Step 3: Quality score ─────────────────────────────────────────────────
    quality = compute_quality_score(parse_result, recon)
    document.derived_quality_score = quality

    if not parse_result.transactions:
        document.processed_at = datetime.now(timezone.utc)
        return

    # ── Step 4: Resolve bank entity ───────────────────────────────────────────
    bank_entity_id = await resolve_entity(
        parse_result.bank_hint or "", db, ai_provider, document_id=document.id
    )

    # ── Step 5: Match / create person ────────────────────────────────────────
    person_id = await match_or_create_person(parse_result.person_hint, db)

    # ── Step 6: Match / create account ──────────────────────────────────────
    account = await match_or_create_account(parse_result, bank_entity_id, person_id, db)

    # Update account balance if reconciliation passed
    if (
        recon.status == ReconciliationStatus.passed
        and parse_result.closing_balance is not None
        and parse_result.statement_date is not None
    ):
        if (
            account.balance_as_of is None
            or parse_result.statement_date >= account.balance_as_of
        ):
            account.last_known_balance = parse_result.closing_balance
            account.balance_as_of = parse_result.statement_date

    # ── Step 7: Create transactions ──────────────────────────────────────────
    await build_transactions(
        document=document,
        parse_result=parse_result,
        account=account,
        quality_score=quality,
        db=db,
        ai_provider=ai_provider,
    )

    document.processed_at = datetime.now(timezone.utc)
    logger.info(
        "Document %s processed: %d txns, recon=%s, quality=%.2f",
        document.id,
        len(parse_result.transactions),
        recon.status.value,
        quality,
    )


def _extract_pdf_bytes(pdf_bytes: bytes, filename: str) -> str:
    """Write PDF bytes to a temp file, extract text, return it."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        try:
            return extract_pdf_text(Path(tmp.name))
        except Exception as exc:
            logger.warning("PDF text extraction failed for %r: %s", filename, exc)
            return ""
