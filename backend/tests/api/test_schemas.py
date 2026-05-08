"""Schema validation unit tests — no DB, no HTTP.

Tests the Pydantic layer: validators, required fields, serialization.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.models.enums import (
    CategorySource,
    Currency,
    MatchType,
    RuleSource,
    TransactionDirection,
)
from app.schemas.category_rule import CategoryRuleCreate
from app.schemas.transaction import TransactionOut


class TestTransactionOut:
    """currency must always be present — a non-negotiable from CLAUDE.md."""

    def _make(self, **overrides):
        defaults = dict(
            id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            date=date(2026, 4, 1),
            posted_date=None,
            description_raw="SUPERMERCADO ABC",
            description_normalized="supermercado abc",
            merchant_entity_id=None,
            amount=Decimal("12500.00"),
            direction=TransactionDirection.debit,
            currency=Currency.CRC,
            category_id=None,
            category_source=None,
            needs_review=False,
            created_at=datetime.now(timezone.utc),
        )
        return TransactionOut(**{**defaults, **overrides})

    def test_currency_present_crc(self):
        t = self._make(currency=Currency.CRC)
        assert t.currency == Currency.CRC

    def test_currency_present_usd(self):
        t = self._make(currency=Currency.USD)
        assert t.currency == Currency.USD

    def test_currency_in_serialized_dict(self):
        t = self._make(currency=Currency.CRC)
        d = t.model_dump()
        assert "currency" in d
        assert d["currency"] == Currency.CRC

    def test_currency_missing_raises(self):
        with pytest.raises(Exception):
            TransactionOut(
                id=uuid.uuid4(),
                account_id=uuid.uuid4(),
                date=date(2026, 4, 1),
                posted_date=None,
                description_raw="X",
                description_normalized="x",
                merchant_entity_id=None,
                amount=Decimal("1.00"),
                direction=TransactionDirection.debit,
                # currency intentionally omitted
                category_id=None,
                category_source=None,
                needs_review=False,
                created_at=datetime.now(timezone.utc),
            )

    def test_amounts_are_decimal(self):
        t = self._make(amount=Decimal("1234.56"))
        assert isinstance(t.amount, Decimal)


class TestCategoryRuleCreate:
    def test_entity_only_valid(self):
        rule = CategoryRuleCreate(
            entity_id=uuid.uuid4(),
            match_type=MatchType.any,
            category_id=uuid.uuid4(),
        )
        assert rule.entity_id is not None

    def test_memo_only_valid(self):
        rule = CategoryRuleCreate(
            memo_pattern="supermercado",
            match_type=MatchType.contains,
            category_id=uuid.uuid4(),
        )
        assert rule.memo_pattern == "supermercado"

    def test_both_valid(self):
        rule = CategoryRuleCreate(
            entity_id=uuid.uuid4(),
            memo_pattern="supermercado",
            match_type=MatchType.contains,
            category_id=uuid.uuid4(),
        )
        assert rule.entity_id is not None
        assert rule.memo_pattern is not None

    def test_neither_raises(self):
        with pytest.raises(Exception, match="entity_id o memo_pattern"):
            CategoryRuleCreate(
                entity_id=None,
                memo_pattern=None,
                match_type=MatchType.any,
                category_id=uuid.uuid4(),
            )

    def test_default_priority(self):
        rule = CategoryRuleCreate(
            entity_id=uuid.uuid4(),
            match_type=MatchType.any,
            category_id=uuid.uuid4(),
        )
        assert rule.priority == 50

    def test_default_source_user_confirmed(self):
        rule = CategoryRuleCreate(
            entity_id=uuid.uuid4(),
            match_type=MatchType.any,
            category_id=uuid.uuid4(),
        )
        assert rule.source == RuleSource.user_confirmed
