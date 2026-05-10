from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.models.entity import Entity
from app.models.entity_pattern import EntityPattern
from app.models.entity_rule import EntityRule
from app.models.enums import MatchType, PatternSource, UnresolvedEntityStatus
from app.models.unresolved_entity_name import UnresolvedEntityName
from app.pipeline.dedup import normalize_description

logger = logging.getLogger(__name__)

# Jaccard thresholds
AUTO_LINK_THRESHOLD = 0.6
SUGGEST_THRESHOLD = 0.4
# Max candidates sent to AI for suggestion
_AI_CANDIDATE_LIMIT = 5


def normalize_entity(raw_name: str) -> str:
    """Canonical form for entity matching — same pipeline as description normalization."""
    return normalize_description(raw_name)


def jaccard_similarity(a: str, b: str) -> float:
    """Token-level Jaccard similarity between two pre-normalized strings."""
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


async def resolve_entity(
    raw_name: str,
    db: AsyncSession,
    ai_provider: AIProvider,
    document_id: Optional[UUID] = None,
) -> Optional[UUID]:
    """Resolve a raw entity name to an entity_id using the 5-step algorithm.

    Steps:
      1. Exact match on entity_patterns.pattern (case-insensitive)
      2. Normalized match on entity_patterns.normalized
      3. Token-overlap (Jaccard) — auto-link ≥0.6, suggest 0.4–0.6
      4. AI suggestion against top candidates
      5. No match → create/update unresolved record

    Returns entity_id on match, None if unresolved.
    """
    if not raw_name or not raw_name.strip():
        return None

    normalized = normalize_entity(raw_name)

    # ── Step 1: exact pattern match ──────────────────────────────────────────
    entity_id = (await db.execute(
        select(EntityPattern.entity_id)
        .where(EntityPattern.pattern.ilike(raw_name))
        .limit(1)
    )).scalar_one_or_none()
    if entity_id:
        return entity_id

    # ── Step 2: normalized match ─────────────────────────────────────────────
    entity_id = (await db.execute(
        select(EntityPattern.entity_id)
        .where(EntityPattern.normalized == normalized)
        .limit(1)
    )).scalar_one_or_none()
    if entity_id:
        return entity_id

    # ── Step 3: token overlap ────────────────────────────────────────────────
    all_patterns = (await db.execute(
        select(EntityPattern.entity_id, EntityPattern.normalized)
    )).all()

    best_id: Optional[UUID] = None
    best_score = 0.0
    for ep_entity_id, ep_normalized in all_patterns:
        score = jaccard_similarity(normalized, ep_normalized or "")
        if score > best_score:
            best_score = score
            best_id = ep_entity_id

    if best_score >= AUTO_LINK_THRESHOLD and best_id:
        logger.info(
            "Entity auto-linked: %r → %s (Jaccard=%.2f)", raw_name, best_id, best_score
        )
        await _add_pattern(raw_name, normalized, best_id, PatternSource.auto_detected, db)
        return best_id

    suggested_entity_id: Optional[UUID] = best_id if best_score >= SUGGEST_THRESHOLD else None
    suggestion_confidence: Optional[float] = best_score if best_score >= SUGGEST_THRESHOLD else None

    # ── Step 3b: entity rules ────────────────────────────────────────────────
    rules = (
        await db.execute(
            select(EntityRule).order_by(EntityRule.priority.desc())
        )
    ).scalars().all()
    for rule in rules:
        if _rule_matches(rule, normalized):
            logger.info("Entity rule matched: %r → %s (rule %s)", raw_name, rule.entity_id, rule.id)
            await _add_pattern(raw_name, normalized, rule.entity_id, PatternSource.auto_detected, db)
            return rule.entity_id

    # ── Step 4: AI suggestion ────────────────────────────────────────────────
    if suggested_entity_id is None:
        candidate_names = (await db.execute(
            select(Entity.canonical_name).limit(_AI_CANDIDATE_LIMIT)
        )).scalars().all()

        if candidate_names:
            ai_match = await ai_provider.suggest_entity_match(raw_name, list(candidate_names))
            if ai_match:
                ai_entity_id = (await db.execute(
                    select(Entity.id)
                    .where(Entity.canonical_name == ai_match)
                    .limit(1)
                )).scalar_one_or_none()
                if ai_entity_id:
                    logger.info("Entity AI-linked: %r → %s", raw_name, ai_entity_id)
                    await _add_pattern(
                        raw_name, normalized, ai_entity_id, PatternSource.ai_suggested, db
                    )
                    return ai_entity_id

    # ── Step 5: no match — queue for user review ─────────────────────────────
    await _upsert_unresolved(
        raw_name, normalized, document_id, suggested_entity_id, suggestion_confidence, db
    )
    logger.info("Entity unresolved: %r (suggestion_confidence=%.2f)", raw_name, suggestion_confidence or 0.0)
    return None


async def _add_pattern(
    raw_name: str,
    normalized: str,
    entity_id: UUID,
    source: PatternSource,
    db: AsyncSession,
) -> None:
    """Add raw_name as a new pattern for an entity (idempotent via ON CONFLICT DO NOTHING)."""
    stmt = (
        pg_insert(EntityPattern)
        .values(pattern=raw_name, normalized=normalized, entity_id=entity_id, source=source)
        .on_conflict_do_nothing()
    )
    await db.execute(stmt)


def _rule_matches(rule: EntityRule, description_normalized: str) -> bool:
    """Test whether a normalized description satisfies an entity rule."""
    import re
    p = (rule.memo_pattern or "").lower()
    d = description_normalized.lower()
    if rule.match_type == MatchType.contains:
        return p in d
    if rule.match_type == MatchType.starts_with:
        return d.startswith(p)
    if rule.match_type == MatchType.exact:
        return d == p
    if rule.match_type == MatchType.regex:
        return bool(re.search(rule.memo_pattern or "", d, re.IGNORECASE))
    if rule.match_type == MatchType.any:
        return True
    return False


async def _upsert_unresolved(
    raw_name: str,
    normalized: str,
    document_id: Optional[UUID],
    suggested_entity_id: Optional[UUID],
    suggestion_confidence: Optional[float],
    db: AsyncSession,
) -> None:
    """Create an unresolved record, or do nothing if one already exists for this name."""
    stmt = (
        pg_insert(UnresolvedEntityName)
        .values(
            raw_name=raw_name,
            normalized=normalized,
            document_id=document_id,
            suggested_entity_id=suggested_entity_id,
            suggestion_confidence=suggestion_confidence,
            status=UnresolvedEntityStatus.pending,
        )
        .on_conflict_do_nothing(constraint="uq_unresolved_entity_normalized")
    )
    await db.execute(stmt)
