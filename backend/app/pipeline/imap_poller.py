"""IMAP poller — fetches new bank statement emails and persists them.

Connects to the configured IMAP server, searches UNSEEN messages in the
configured folder, stores each raw .eml file to disk, and inserts an Email
row (status=pending).  Dedup is handled via the UNIQUE constraint on
message_id: if a message was already processed, the INSERT is skipped and
the message is silently ignored.

Returns a list of (email_id, raw_path) tuples for every newly inserted row,
so the caller can trigger the pipeline.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from imapclient import IMAPClient
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.email_model import Email
from app.models.enums import EmailStatus
from app.pipeline.email_parser import parse_raw_email

logger = logging.getLogger(__name__)

# Where raw .eml files are stored inside the container / on the host mount.
_RAW_EMAIL_DIR = Path(os.environ.get("RAW_EMAIL_DIR", "/data/raw_emails"))


async def poll_and_ingest(db: AsyncSession) -> list[UUID]:
    """Fetch UNSEEN emails from IMAP and insert pending Email rows.

    Returns list of email IDs that were newly inserted (skips duplicates).
    """
    if not settings.imap_host or not settings.imap_user:
        logger.warning("IMAP not configured — skipping poll")
        return []

    try:
        raw_messages = _fetch_unseen()
    except Exception as exc:
        logger.error("IMAP fetch failed: %s", exc, exc_info=True)
        return []

    _RAW_EMAIL_DIR.mkdir(parents=True, exist_ok=True)

    new_ids: list[UUID] = []
    for message_id, raw_bytes in raw_messages:
        email_id = await _ingest_one(message_id, raw_bytes, db)
        if email_id:
            new_ids.append(email_id)

    return new_ids


def _fetch_unseen() -> list[tuple[str, bytes]]:
    """Open IMAP connection, search UNSEEN, download, mark SEEN.  Sync."""
    results: list[tuple[str, bytes]] = []

    with IMAPClient(
        host=settings.imap_host,
        port=settings.imap_port,
        ssl=True,
        timeout=30,
    ) as client:
        client.login(settings.imap_user, settings.imap_password)
        client.select_folder(settings.imap_folder, readonly=False)

        uids = client.search(["UNSEEN"])
        if not uids:
            return results

        logger.info("IMAP: %d unseen message(s) found", len(uids))

        for uid, data in client.fetch(uids, ["RFC822", "ENVELOPE"]).items():
            raw: bytes = data[b"RFC822"]
            envelope = data.get(b"ENVELOPE")

            # Use the IMAP ENVELOPE message-id if available, else fallback
            message_id = _envelope_message_id(envelope) or f"uid-{uid}"
            results.append((message_id, raw))

            # Mark as SEEN so we don't fetch it again on next poll
            client.add_flags([uid], [b"\\Seen"])

    return results


def _envelope_message_id(envelope) -> Optional[str]:
    """Extract message-id string from an imapclient Envelope object."""
    if envelope is None:
        return None
    mid = getattr(envelope, "message_id", None)
    if mid is None:
        return None
    if isinstance(mid, bytes):
        mid = mid.decode(errors="replace")
    return mid.strip("<>").strip() or None


async def _ingest_one(
    message_id: str,
    raw_bytes: bytes,
    db: AsyncSession,
) -> Optional[UUID]:
    """Persist a single raw email.  Returns new UUID or None if duplicate."""
    # Quick duplicate check before touching disk
    existing = (
        await db.execute(select(Email.id).where(Email.message_id == message_id))
    ).scalar_one_or_none()
    if existing:
        logger.debug("Skipping duplicate message_id=%r", message_id)
        return None

    # Parse headers for metadata only (body/attachments handled later)
    try:
        parsed = parse_raw_email(raw_bytes)
    except Exception as exc:
        logger.warning("Could not parse headers for %r: %s", message_id, exc)
        parsed = None  # type: ignore[assignment]

    # Write .eml to disk
    safe_id = message_id.replace("/", "_").replace(" ", "_")[:100]
    path = _RAW_EMAIL_DIR / f"{safe_id}.eml"
    path.write_bytes(raw_bytes)
    logger.info("Stored raw email → %s", path)

    # Insert Email row (ON CONFLICT DO NOTHING for race safety)
    received_at = (parsed.received_at if parsed else datetime.now(timezone.utc))
    stmt = (
        pg_insert(Email)
        .values(
            message_id=message_id,
            received_at=received_at,
            sender=parsed.sender if parsed else None,
            subject=parsed.subject if parsed else None,
            status=EmailStatus.pending,
            raw_stored_path=str(path),
        )
        .on_conflict_do_nothing(constraint="uq_emails_message_id")
        .returning(Email.id)
    )
    result = await db.execute(stmt)
    row = result.fetchone()
    if row is None:
        logger.debug("Race: message_id=%r already inserted", message_id)
        return None

    await db.flush()
    logger.info("Ingested email id=%s subject=%r", row[0], parsed.subject if parsed else "?")
    return row[0]
