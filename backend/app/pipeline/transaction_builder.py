from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider, FinancialParseResult
from app.models.account import Account
from app.models.category_rule import CategoryRule
from app.models.document import Document
from app.models.enums import AccountType, Currency, PatternSource
from app.models.entity import Entity
from app.models.entity_pattern import EntityPattern
from app.models.person import Person
from app.models.transaction import Transaction
from app.models.transaction_document import TransactionDocument
from app.pipeline.dedup import compute_dedup_key, normalize_description
from app.pipeline.entity_resolver import resolve_entity
from app.pipeline.quality_score import REVIEW_THRESHOLD
from app.pipeline.rule_engine import apply_rules

logger = logging.getLogger(__name__)


async def match_or_create_person(person_hint: Optional[str], db: AsyncSession) -> uuid.UUID:
    """Find a Person by name or create one from the hint.

    Matching is case-insensitive. Falls back to creating a new Person if no
    name hint is provided or no match is found.
    """
    if person_hint:
        row = (await db.execute(
            select(Person.id).where(Person.name.ilike(person_hint)).limit(1)
        )).scalar_one_or_none()
        if row:
            return row

        # Create new person from document hint
        person = Person(name=person_hint)
        db.add(person)
        await db.flush()
        logger.info("Created new person from hint: %r", person_hint)
        return person.id

    # No hint — return first person (family app assumption) or create unknown
    row = (await db.execute(select(Person.id).limit(1))).scalar_one_or_none()
    if row:
        return row

    person = Person(name="Unknown")
    db.add(person)
    await db.flush()
    return person.id


async def match_or_create_account(
    parse_result: FinancialParseResult,
    bank_entity_id: Optional[uuid.UUID],
    person_id: uuid.UUID,
    db: AsyncSession,
) -> Account:
    """Find an Account matching (person, account_hint, bank) or create one.

    The account is created unconfirmed so the user reviews it in the UI.
    """
    account_hint = parse_result.account_hint
    currency = parse_result.currency or Currency.CRC

    if account_hint and bank_entity_id:
        row = (await db.execute(
            select(Account).where(
                Account.person_id == person_id,
                Account.account_number_hint == account_hint,
                Account.bank_entity_id == bank_entity_id,
            ).limit(1)
        )).scalar_one_or_none()
        if row:
            return row

    # Also try matching by hint alone (without bank) as a fallback
    if account_hint:
        row = (await db.execute(
            select(Account).where(
                Account.person_id == person_id,
                Account.account_number_hint == account_hint,
            ).limit(1)
        )).scalar_one_or_none()
        if row:
            return row

    account = Account(
        person_id=person_id,
        bank_entity_id=bank_entity_id,
        account_type=AccountType.savings,
        currency=currency,
        account_number_hint=account_hint,
        confirmed=False,
    )
    db.add(account)
    await db.flush()
    logger.info("Created new account: hint=%r currency=%s", account_hint, currency)
    return account


async def build_transactions(
    document: Document,
    parse_result: FinancialParseResult,
    account: Account,
    quality_score: float,
    db: AsyncSession,
    ai_provider: AIProvider,
) -> list[uuid.UUID]:
    """Create Transaction rows from a FinancialParseResult.

    Handles dedup via ON CONFLICT DO NOTHING; links both new and existing
    transactions to the source document via transaction_documents.

    Transactions from low-quality documents (score < REVIEW_THRESHOLD) or
    those without a category are flagged needs_review=True.
    """
    force_review = quality_score < REVIEW_THRESHOLD

    # Load all rules once per document
    rules: list[CategoryRule] = list(
        (await db.execute(select(CategoryRule))).scalars().all()
    )

    transaction_ids: list[uuid.UUID] = []

    for txn in parse_result.transactions:
        desc_norm = normalize_description(txn.description)
        dedup_key = compute_dedup_key(
            account.id, txn.date, txn.amount, txn.direction.value, desc_norm
        )

        # Resolve merchant entity for rule matching
        merchant_entity_id = await resolve_entity(
            txn.description, db, ai_provider, document_id=document.id
        )

        category_id, category_source, is_transfer = apply_rules(rules, merchant_entity_id, desc_norm)
        needs_review = force_review or (category_id is None and not is_transfer)

        # INSERT ... ON CONFLICT DO NOTHING RETURNING id
        stmt = (
            pg_insert(Transaction)
            .values(
                id=uuid.uuid4(),
                account_id=account.id,
                date=txn.date,
                posted_date=txn.posted_date,
                description_raw=txn.description,
                description_normalized=desc_norm,
                merchant_entity_id=merchant_entity_id,
                amount=txn.amount,
                direction=txn.direction,
                currency=account.currency,
                category_id=category_id,
                category_source=category_source,
                dedup_key=dedup_key,
                needs_review=needs_review,
                is_transfer=is_transfer,
            )
            .on_conflict_do_nothing(constraint="uq_transactions_account_dedup")
            .returning(Transaction.id)
        )
        result = await db.execute(stmt)
        row = result.fetchone()

        if row:
            txn_id: uuid.UUID = row[0]
            logger.debug("Inserted transaction %s", txn_id)
        else:
            # Conflict — fetch existing
            txn_id = (await db.execute(
                select(Transaction.id).where(
                    Transaction.account_id == account.id,
                    Transaction.dedup_key == dedup_key,
                )
            )).scalar_one()
            logger.debug("Dedup hit for transaction %s", txn_id)

        # Link transaction ↔ document (idempotent)
        link_stmt = (
            pg_insert(TransactionDocument)
            .values(transaction_id=txn_id, document_id=document.id)
            .on_conflict_do_nothing()
        )
        await db.execute(link_stmt)

        transaction_ids.append(txn_id)

    return transaction_ids
