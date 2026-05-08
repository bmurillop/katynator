"""Add income_source to entity_type enum

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-08
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL requires committing the current transaction before ALTER TYPE
    op.execute("COMMIT")
    op.execute("ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'income_source'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; mark affected rows as 'other'
    op.execute("UPDATE entities SET type = 'other' WHERE type = 'income_source'")
