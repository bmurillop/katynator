"""
AIProvider abstract base class, shared data types, and shared parsing utilities.
All providers import from here; nothing here imports from a specific provider.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field, ValidationError

from app.models.enums import Currency, TransactionDirection

# ── Jinja2 template environment ──────────────────────────────────────────────

_PROMPT_DIR = Path(__file__).parent / "prompts"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_PROMPT_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_prompt(text: str) -> str:
    """Render the extraction prompt with the given document text."""
    return _jinja_env.get_template("parse_statement.jinja2").render(text=text)


def render_system_prompt() -> str:
    """Render the prompt with no document — used as the cacheable system message for Claude."""
    return _jinja_env.get_template("parse_statement.jinja2").render(text="")


# ── Result types ─────────────────────────────────────────────────────────────

class ParsedTransaction(BaseModel):
    date: date
    posted_date: Optional[date] = None
    description: str
    amount: Decimal
    direction: TransactionDirection


class FinancialParseResult(BaseModel):
    account_hint: Optional[str] = None
    bank_hint: Optional[str] = None
    person_hint: Optional[str] = None
    currency: Optional[Currency] = None
    statement_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    opening_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    claimed_debit_count: Optional[int] = None
    claimed_debit_total: Optional[Decimal] = None
    claimed_credit_count: Optional[int] = None
    claimed_credit_total: Optional[Decimal] = None
    transactions: list[ParsedTransaction] = Field(default_factory=list)

    # Debug only — excluded from model_dump() / serialization
    raw_response: Optional[str] = Field(default=None, exclude=True)


# ── Errors ───────────────────────────────────────────────────────────────────

class AIParseError(Exception):
    def __init__(self, message: str, raw_response: str = ""):
        super().__init__(message)
        self.raw_response = raw_response


# ── Shared response parser ────────────────────────────────────────────────────

def parse_llm_response(raw: str) -> FinancialParseResult:
    """
    Extract a FinancialParseResult from a raw LLM response string.
    Strips markdown code fences and tolerates minor leading/trailing prose.
    """
    text = raw.strip()

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    # Try parsing as-is first
    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fall back: find the outermost JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise AIParseError("No JSON object found in LLM response", raw)
        try:
            data = json.loads(text[start:end])
        except json.JSONDecodeError as exc:
            raise AIParseError(f"Invalid JSON in LLM response: {exc}", raw) from exc

    try:
        result = FinancialParseResult.model_validate(data)
        result.raw_response = raw
        return result
    except ValidationError as exc:
        raise AIParseError(f"LLM response does not match expected schema: {exc}", raw) from exc


# ── Abstract base ─────────────────────────────────────────────────────────────

class AIProvider(ABC):

    @abstractmethod
    async def parse_financial_document(self, text: str) -> FinancialParseResult:
        """Extract structured transaction data from the plain text of a financial document."""

    @abstractmethod
    async def suggest_entity_match(
        self, raw_name: str, candidates: list[str]
    ) -> str | None:
        """Return the best-matching candidate for raw_name, or None if none match well."""

    @abstractmethod
    async def suggest_category(
        self, description: str, available_categories: list[str]
    ) -> str | None:
        """Return the best-matching category for a transaction description, or None."""
