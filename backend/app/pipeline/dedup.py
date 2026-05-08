from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date
from decimal import Decimal
from uuid import UUID

# Leading run of ≥6 consecutive digits followed by whitespace is a bank-internal
# reference ID (e.g. BNCR "99837153 ..."). Strip it before hashing so the same
# transaction maps to the same key across different statement re-issues.
_REF_PREFIX = re.compile(r"^\d{6,}\s+")
# Non-word, non-space characters (punctuation / special chars)
_PUNCT = re.compile(r"[^\w\s]")
# Runs of whitespace → single space
_MULTI_SPACE = re.compile(r"\s+")


def normalize_description(description: str) -> str:
    """Canonical form used for dedup_key and fuzzy entity matching.

    Steps: lowercase → NFKD accent-strip → ref-ID strip → punctuation strip
    → collapse whitespace.
    """
    text = description.lower()
    # Unicode decompose + drop combining marks (accents)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Drop bank-internal numeric reference prefix
    text = _REF_PREFIX.sub("", text)
    # Remove punctuation
    text = _PUNCT.sub(" ", text)
    # Collapse whitespace
    return _MULTI_SPACE.sub(" ", text).strip()


def compute_dedup_key(
    account_id: UUID,
    txn_date: date,
    amount: Decimal,
    direction: str,
    normalized_description: str,
) -> str:
    """SHA-256 hex digest of the transaction's natural key.

    All fields are pipe-separated so a partial match can never collide with
    a full match.
    """
    payload = (
        f"{account_id}"
        f"|{txn_date.isoformat()}"
        f"|{amount:.2f}"
        f"|{direction}"
        f"|{normalized_description}"
    )
    return hashlib.sha256(payload.encode()).hexdigest()
