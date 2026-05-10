"""Add is_transfer to transactions and sets_transfer to category_rules

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Mark transactions as internal transfers (excluded from reports)
    op.add_column(
        "transactions",
        sa.Column("is_transfer", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Transfer rules: sets_transfer = True means rule marks transaction as transfer
    # instead of setting a category, so category_id becomes optional
    op.add_column(
        "category_rules",
        sa.Column("sets_transfer", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.alter_column("category_rules", "category_id", nullable=True)
    op.create_check_constraint(
        "ck_rule_has_category_or_transfer",
        "category_rules",
        "category_id IS NOT NULL OR sets_transfer = TRUE",
    )


def downgrade() -> None:
    op.drop_constraint("ck_rule_has_category_or_transfer", "category_rules", type_="check")
    # Remove transfer rules before restoring NOT NULL on category_id
    op.execute("DELETE FROM category_rules WHERE sets_transfer = TRUE AND category_id IS NULL")
    op.alter_column("category_rules", "category_id", nullable=False)
    op.drop_column("category_rules", "sets_transfer")
    op.drop_column("transactions", "is_transfer")
