from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.category_rule import CategoryRule
from app.models.enums import CategorySource, MatchType, RuleSource
from app.pipeline.rule_engine import apply_rules


def _rule(
    *,
    entity_id=None,
    memo_pattern=None,
    match_type=MatchType.any,
    category_id=None,
    priority=50,
) -> CategoryRule:
    """Build a CategoryRule without a DB session for unit testing."""
    r = CategoryRule()
    r.id = uuid4()
    r.entity_id = entity_id
    r.memo_pattern = memo_pattern
    r.match_type = match_type
    r.category_id = category_id or uuid4()
    r.priority = priority
    r.source = RuleSource.user_confirmed
    r.created_at = datetime.now(timezone.utc)
    return r


CAT_GROCERIES = uuid4()
CAT_EDUCATION = uuid4()
CAT_TRANSFERS = uuid4()
CAT_UTILITIES = uuid4()
ENTITY_PAOLA = uuid4()
ENTITY_OTHER = uuid4()


class TestNoRules:
    def test_empty_rules_returns_none(self):
        cat_id, source, _ = apply_rules([], None, "supermercado")
        assert cat_id is None
        assert source is None


class TestMatchTypeAny:
    def test_entity_rule_matches_any_description(self):
        rule = _rule(entity_id=ENTITY_PAOLA, match_type=MatchType.any, category_id=CAT_TRANSFERS)
        cat_id, source, _ = apply_rules([rule], ENTITY_PAOLA, "angie beca")
        assert cat_id == CAT_TRANSFERS
        assert source == CategorySource.rule

    def test_entity_rule_does_not_match_different_entity(self):
        rule = _rule(entity_id=ENTITY_PAOLA, match_type=MatchType.any, category_id=CAT_TRANSFERS)
        cat_id, source, _ = apply_rules([rule], ENTITY_OTHER, "angie beca")
        assert cat_id is None

    def test_null_entity_rule_matches_any_entity(self):
        rule = _rule(entity_id=None, match_type=MatchType.any, category_id=CAT_GROCERIES)
        cat_id, _, __ = apply_rules([rule], ENTITY_PAOLA, "supermercado")
        assert cat_id == CAT_GROCERIES

    def test_null_entity_rule_matches_null_entity(self):
        rule = _rule(entity_id=None, match_type=MatchType.any, category_id=CAT_GROCERIES)
        cat_id, _, __ = apply_rules([rule], None, "supermercado")
        assert cat_id == CAT_GROCERIES


class TestMatchTypeContains:
    def test_contains_match(self):
        rule = _rule(
            entity_id=ENTITY_PAOLA,
            memo_pattern="beca",
            match_type=MatchType.contains,
            category_id=CAT_EDUCATION,
        )
        cat_id, _, __ = apply_rules([rule], ENTITY_PAOLA, "angie 202616 beca 36")
        assert cat_id == CAT_EDUCATION

    def test_contains_case_insensitive(self):
        rule = _rule(memo_pattern="BECA", match_type=MatchType.contains, category_id=CAT_EDUCATION)
        cat_id, _, __ = apply_rules([rule], None, "angie beca 36")
        assert cat_id == CAT_EDUCATION

    def test_contains_no_match(self):
        rule = _rule(memo_pattern="beca", match_type=MatchType.contains, category_id=CAT_EDUCATION)
        cat_id, _, __ = apply_rules([rule], None, "planchado mayo 2026")
        assert cat_id is None


class TestMatchTypeExact:
    def test_exact_match(self):
        rule = _rule(memo_pattern="supermercado perimercado", match_type=MatchType.exact, category_id=CAT_GROCERIES)
        cat_id, _, __ = apply_rules([rule], None, "supermercado perimercado")
        assert cat_id == CAT_GROCERIES

    def test_exact_no_partial_match(self):
        rule = _rule(memo_pattern="supermercado", match_type=MatchType.exact, category_id=CAT_GROCERIES)
        cat_id, _, __ = apply_rules([rule], None, "supermercado perimercado")
        assert cat_id is None


class TestMatchTypeRegex:
    def test_regex_match(self):
        rule = _rule(memo_pattern=r"pago\s+icetel", match_type=MatchType.regex, category_id=CAT_UTILITIES)
        cat_id, _, __ = apply_rules([rule], None, "pago icetel 88405817")
        assert cat_id == CAT_UTILITIES

    def test_regex_case_insensitive(self):
        rule = _rule(memo_pattern=r"PAGO\s+ICETEL", match_type=MatchType.regex, category_id=CAT_UTILITIES)
        cat_id, _, __ = apply_rules([rule], None, "pago icetel 24541926")
        assert cat_id == CAT_UTILITIES

    def test_invalid_regex_does_not_crash(self):
        rule = _rule(memo_pattern=r"[invalid(", match_type=MatchType.regex, category_id=CAT_UTILITIES)
        cat_id, _, __ = apply_rules([rule], None, "anything")
        assert cat_id is None


class TestPriority:
    def test_higher_priority_wins(self):
        low = _rule(entity_id=None, match_type=MatchType.any, category_id=CAT_GROCERIES, priority=25)
        high = _rule(entity_id=None, match_type=MatchType.any, category_id=CAT_EDUCATION, priority=100)
        cat_id, _, __ = apply_rules([low, high], None, "anything")
        assert cat_id == CAT_EDUCATION

    def test_entity_plus_memo_beats_entity_only(self):
        # entity-only rule (priority 50) vs entity+memo rule (priority 100)
        entity_only = _rule(
            entity_id=ENTITY_PAOLA, match_type=MatchType.any,
            category_id=CAT_TRANSFERS, priority=50,
        )
        entity_memo = _rule(
            entity_id=ENTITY_PAOLA, memo_pattern="beca",
            match_type=MatchType.contains, category_id=CAT_EDUCATION, priority=100,
        )
        cat_id, _, __ = apply_rules([entity_only, entity_memo], ENTITY_PAOLA, "angie beca 36")
        assert cat_id == CAT_EDUCATION

    def test_entity_only_fallback_when_memo_no_match(self):
        entity_only = _rule(
            entity_id=ENTITY_PAOLA, match_type=MatchType.any,
            category_id=CAT_TRANSFERS, priority=50,
        )
        entity_memo = _rule(
            entity_id=ENTITY_PAOLA, memo_pattern="beca",
            match_type=MatchType.contains, category_id=CAT_EDUCATION, priority=100,
        )
        # Description doesn't contain "beca" → falls through to entity-only rule
        cat_id, _, __ = apply_rules([entity_only, entity_memo], ENTITY_PAOLA, "chuchu rojo")
        assert cat_id == CAT_TRANSFERS
