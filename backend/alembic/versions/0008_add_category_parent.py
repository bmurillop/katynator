"""Add parent_id to categories for one-level subcategory support

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("parent_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_categories_parent_id",
        "categories",
        "categories",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Replace global name uniqueness with per-level uniqueness so "Misc" can
    # appear as a subcategory under multiple parents.
    op.drop_constraint("uq_categories_name", "categories", type_="unique")
    op.create_index(
        "uq_categories_name_toplevel",
        "categories",
        ["name"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NULL"),
    )
    op.create_index(
        "uq_categories_name_child",
        "categories",
        ["name", "parent_id"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_categories_name_child", table_name="categories")
    op.drop_index("uq_categories_name_toplevel", table_name="categories")
    op.drop_constraint("fk_categories_parent_id", "categories", type_="foreignkey")
    op.drop_column("categories", "parent_id")
    op.create_unique_constraint("uq_categories_name", "categories", ["name"])
