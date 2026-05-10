"""Add starts_with to match_type enum

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-09
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("COMMIT")
    op.execute("ALTER TYPE match_type ADD VALUE IF NOT EXISTS 'starts_with'")


def downgrade() -> None:
    op.execute("UPDATE category_rules SET match_type = 'contains' WHERE match_type = 'starts_with'")
