"""Add unresolved_entity_names table

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE unresolved_entity_status AS ENUM "
        "('pending', 'matched', 'created', 'ignored')"
    )
    op.create_table(
        "unresolved_entity_names",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("raw_name", sa.Text, nullable=False),
        sa.Column("normalized", sa.Text, nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "suggested_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("suggestion_confidence", sa.Float, nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "matched", "created", "ignored",
                            name="unresolved_entity_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "resolved_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("normalized", name="uq_unresolved_entity_normalized"),
    )


def downgrade() -> None:
    op.drop_table("unresolved_entity_names")
    op.execute("DROP TYPE unresolved_entity_status")
