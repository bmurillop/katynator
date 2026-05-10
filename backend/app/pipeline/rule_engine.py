from __future__ import annotations

import re
import uuid
from typing import Optional

from app.models.category_rule import CategoryRule
from app.models.enums import CategorySource, MatchType


def apply_rules(
    rules: list[CategoryRule],
    entity_id: Optional[uuid.UUID],
    description_normalized: str,
) -> tuple[Optional[uuid.UUID], Optional[CategorySource], bool]:
    """Two-tier category/transfer rule resolution.

    Returns (category_id, CategorySource.rule, is_transfer) on the first match.
    Transfer rules return (None, None, True); category rules return (category_id, rule, False).
    Returns (None, None, False) when no rule matches.

    Rules are sorted by priority DESC then created_at DESC before evaluation so
    the most specific / most recent rule wins ties.

    Callers are responsible for loading the relevant rules from the DB before
    calling this function (keeps it pure and testable).
    """
    candidates = [r for r in rules if r.entity_id == entity_id or r.entity_id is None]

    def _sort_key(r: CategoryRule) -> tuple[int, float]:
        ts = r.created_at.timestamp() if r.created_at else 0.0
        return (-r.priority, -ts)

    candidates.sort(key=_sort_key)

    for rule in candidates:
        if _memo_matches(rule, description_normalized):
            if rule.sets_transfer:
                return None, None, True
            return rule.category_id, CategorySource.rule, False

    return None, None, False


def _memo_matches(rule: CategoryRule, description_normalized: str) -> bool:
    match rule.match_type:
        case MatchType.any:
            return True
        case MatchType.contains:
            return (rule.memo_pattern or "").lower() in description_normalized
        case MatchType.starts_with:
            return description_normalized.startswith((rule.memo_pattern or "").lower())
        case MatchType.exact:
            return (rule.memo_pattern or "").lower() == description_normalized
        case MatchType.regex:
            try:
                return bool(
                    re.search(rule.memo_pattern or "", description_normalized, re.IGNORECASE)
                )
            except re.error:
                return False
        case _:
            return False
