"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-05-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ──────────────────────────────────────────────────────────
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'member')")
    op.execute("CREATE TYPE entity_type AS ENUM ('bank', 'merchant', 'issuer', 'person', 'other')")
    op.execute("CREATE TYPE pattern_source AS ENUM ('auto_detected', 'user_added', 'ai_suggested')")
    op.execute("CREATE TYPE account_type AS ENUM ('checking', 'savings', 'credit_card', 'loan', 'other')")
    op.execute("CREATE TYPE currency AS ENUM ('CRC', 'USD')")
    op.execute("CREATE TYPE transaction_direction AS ENUM ('debit', 'credit')")
    op.execute("CREATE TYPE match_type AS ENUM ('any', 'contains', 'exact', 'regex')")
    op.execute("CREATE TYPE rule_source AS ENUM ('user_confirmed', 'ai_suggested')")
    op.execute("CREATE TYPE category_source AS ENUM ('rule', 'ai_suggested', 'user_set')")
    op.execute("CREATE TYPE email_status AS ENUM ('pending', 'processing', 'processed', 'failed', 'skipped')")
    op.execute("CREATE TYPE doc_type AS ENUM ('pdf', 'html_body', 'plain_text')")
    op.execute("CREATE TYPE reconciliation_status AS ENUM ('passed', 'failed', 'not_applicable')")

    # ── persons ─────────────────────────────────────────────────────────────
    op.create_table(
        "persons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── entities ────────────────────────────────────────────────────────────
    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_name", sa.Text, nullable=False),
        sa.Column("display_name", sa.Text, nullable=True),
        sa.Column("type", postgresql.ENUM(name="entity_type", create_type=False), nullable=False),
        sa.Column("confirmed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── users ───────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("role", postgresql.ENUM(name="user_role", create_type=False), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id"), nullable=True, unique=True),
        sa.Column("must_change_password", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("token_version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # ── entity_patterns ─────────────────────────────────────────────────────
    op.create_table(
        "entity_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("pattern", sa.Text, nullable=False),
        sa.Column("normalized", sa.Text, nullable=False),
        sa.Column("source", postgresql.ENUM(name="pattern_source", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("entity_id", "normalized", name="uq_entity_patterns_entity_normalized"),
    )

    # ── accounts ────────────────────────────────────────────────────────────
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id"), nullable=False),
        sa.Column("bank_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("issuer_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("account_type", postgresql.ENUM(name="account_type", create_type=False), nullable=False),
        sa.Column("currency", postgresql.ENUM(name="currency", create_type=False), nullable=False),
        sa.Column("nickname", sa.Text, nullable=True),
        sa.Column("account_number_hint", sa.Text, nullable=True),
        sa.Column("last_known_balance", sa.Numeric(18, 2), nullable=True),
        sa.Column("balance_as_of", sa.Date, nullable=True),
        sa.Column("confirmed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("person_id", "account_number_hint", "bank_entity_id", name="uq_accounts_person_hint_bank"),
    )

    # ── categories ──────────────────────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("icon", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
    )

    # ── category_rules ──────────────────────────────────────────────────────
    op.create_table(
        "category_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("memo_pattern", sa.Text, nullable=True),
        sa.Column("match_type", postgresql.ENUM(name="match_type", create_type=False), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="50"),
        sa.Column("source", postgresql.ENUM(name="rule_source", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("entity_id", "memo_pattern", "match_type", name="uq_category_rules"),
        sa.CheckConstraint(
            "entity_id IS NOT NULL OR memo_pattern IS NOT NULL",
            name="ck_rule_has_entity_or_memo",
        ),
    )

    # ── emails ──────────────────────────────────────────────────────────────
    op.create_table(
        "emails",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", sa.Text, nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sender", sa.Text, nullable=True),
        sa.Column("subject", sa.Text, nullable=True),
        sa.Column("status", postgresql.ENUM(name="email_status", create_type=False), nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("raw_stored_path", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("message_id", name="uq_emails_message_id"),
    )

    # ── documents ───────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("emails.id"), nullable=False),
        sa.Column("doc_type", postgresql.ENUM(name="doc_type", create_type=False), nullable=False),
        sa.Column("filename", sa.Text, nullable=True),
        sa.Column("extracted_text", sa.Text, nullable=True),
        sa.Column("ai_raw_response", postgresql.JSONB, nullable=True),
        sa.Column("reconciliation_status", postgresql.ENUM(name="reconciliation_status", create_type=False), nullable=True),
        sa.Column("reconciliation_details", postgresql.JSONB, nullable=True),
        sa.Column("derived_quality_score", sa.Float, nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── transactions ────────────────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("posted_date", sa.Date, nullable=True),
        sa.Column("description_raw", sa.Text, nullable=False),
        sa.Column("description_normalized", sa.Text, nullable=False),
        sa.Column("merchant_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("direction", postgresql.ENUM(name="transaction_direction", create_type=False), nullable=False),
        sa.Column("currency", postgresql.ENUM(name="currency", create_type=False), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("category_source", postgresql.ENUM(name="category_source", create_type=False), nullable=True),
        sa.Column("dedup_key", sa.String(64), nullable=False),
        sa.Column("needs_review", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("account_id", "dedup_key", name="uq_transactions_account_dedup"),
    )
    op.create_index("ix_transactions_account_date", "transactions", ["account_id", "date"])
    op.create_index("ix_transactions_category_date", "transactions", ["category_id", "date"])
    op.create_index("ix_transactions_merchant", "transactions", ["merchant_entity_id"])

    # ── transaction_documents ───────────────────────────────────────────────
    op.create_table(
        "transaction_documents",
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.PrimaryKeyConstraint("transaction_id", "document_id", name="pk_transaction_documents"),
    )

    # ── app_settings ────────────────────────────────────────────────────────
    op.create_table(
        "app_settings",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("transaction_documents")
    op.drop_index("ix_transactions_merchant", table_name="transactions")
    op.drop_index("ix_transactions_category_date", table_name="transactions")
    op.drop_index("ix_transactions_account_date", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("documents")
    op.drop_table("emails")
    op.drop_table("category_rules")
    op.drop_table("categories")
    op.drop_table("accounts")
    op.drop_table("entity_patterns")
    op.drop_table("users")
    op.drop_table("entities")
    op.drop_table("persons")

    op.execute("DROP TYPE reconciliation_status")
    op.execute("DROP TYPE doc_type")
    op.execute("DROP TYPE email_status")
    op.execute("DROP TYPE category_source")
    op.execute("DROP TYPE rule_source")
    op.execute("DROP TYPE match_type")
    op.execute("DROP TYPE transaction_direction")
    op.execute("DROP TYPE currency")
    op.execute("DROP TYPE account_type")
    op.execute("DROP TYPE pattern_source")
    op.execute("DROP TYPE entity_type")
    op.execute("DROP TYPE user_role")
