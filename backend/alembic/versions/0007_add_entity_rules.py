"""Add entity_rules table

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entity_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("memo_pattern", sa.Text(), nullable=False),
        sa.Column(
            "match_type",
            sa.Enum("any", "contains", "starts_with", "exact", "regex", name="match_type", create_type=False),
            nullable=False,
            server_default="contains",
        ),
        sa.Column("entity_id", UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column(
            "source",
            sa.Enum("user_confirmed", "ai_suggested", name="rule_source", create_type=False),
            nullable=False,
            server_default="user_confirmed",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.UniqueConstraint("memo_pattern", "match_type", name="uq_entity_rules_pattern_type"),
    )


def downgrade() -> None:
    op.drop_table("entity_rules")
