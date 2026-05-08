"""Seed default system categories

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-08
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CATEGORIES = [
    ("Alimentación",    "#E67E22", "🍔"),
    ("Transporte",      "#3498DB", "🚗"),
    ("Vivienda",        "#8E44AD", "🏠"),
    ("Salud",           "#E74C3C", "💊"),
    ("Entretenimiento", "#F39C12", "🎬"),
    ("Servicios",       "#1ABC9C", "💡"),
    ("Educación",       "#2ECC71", "📚"),
    ("Ropa y Calzado",  "#E91E63", "👕"),
    ("Viajes",          "#00BCD4", "✈️"),
    ("Transferencias",  "#607D8B", "↔"),
    ("Ingresos",        "#27AE60", "💰"),
    ("Otros",           "#95A5A6", "•"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for name, color, icon in _CATEGORIES:
        conn.execute(
            sa.text(
                "INSERT INTO categories (id, name, color, icon, is_system) "
                "VALUES (:id, :name, :color, :icon, true) "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": str(uuid.uuid4()), "name": name, "color": color, "icon": icon},
        )


def downgrade() -> None:
    op.execute("DELETE FROM categories WHERE is_system = true")
