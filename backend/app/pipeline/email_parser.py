from __future__ import annotations

import email as _email_lib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)


@dataclass
class ParsedEmail:
    subject: str
    sender: str
    received_at: datetime
    body_texts: list[str] = field(default_factory=list)
    pdf_attachments: list[tuple[str, bytes]] = field(default_factory=list)


def parse_raw_email(raw: bytes) -> ParsedEmail:
    """Parse a raw .eml byte string into body text and PDF attachments.

    HTML parts are converted to plain text via BeautifulSoup.
    Only PDF attachments are returned; other attachment types are skipped.
    """
    msg = _email_lib.message_from_bytes(raw)

    subject = msg.get("Subject", "")
    sender = msg.get("From", "")
    received_at = _parse_date(msg.get("Date"))

    body_texts: list[str] = []
    pdf_attachments: list[tuple[str, bytes]] = []

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = str(part.get("Content-Disposition", ""))
        is_attachment = "attachment" in disposition

        if content_type == "text/plain" and not is_attachment:
            payload = part.get_payload(decode=True)
            if payload:
                body_texts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))

        elif content_type == "text/html" and not is_attachment:
            payload = part.get_payload(decode=True)
            if payload:
                html = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                body_texts.append(_html_to_text(html))

        elif _is_pdf_part(part, content_type):
            payload = part.get_payload(decode=True)
            if payload:
                filename = part.get_filename() or "attachment.pdf"
                pdf_attachments.append((filename, payload))

    return ParsedEmail(
        subject=subject,
        sender=sender,
        received_at=received_at,
        body_texts=body_texts,
        pdf_attachments=pdf_attachments,
    )


def _is_pdf_part(part, content_type: str) -> bool:
    if content_type == "application/pdf":
        return True
    if content_type == "application/octet-stream":
        filename = part.get_filename() or ""
        return filename.lower().endswith(".pdf")
    return False


def _html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator=" ", strip=True)


def _parse_date(date_str: str | None) -> datetime:
    if date_str:
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            pass
    return datetime.now(timezone.utc)
