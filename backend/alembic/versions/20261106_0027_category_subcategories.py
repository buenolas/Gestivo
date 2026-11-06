"""add one-level financial category hierarchy

Revision ID: 20261106_0027
Revises: 20261106_0026
Create Date: 2026-11-06 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261106_0027"
down_revision: str | None = "20261106_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "financial_categories",
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_financial_categories_parent_id",
        "financial_categories",
        ["parent_id"],
    )
    op.create_foreign_key(
        "fk_financial_categories_parent_id_financial_categories",
        "financial_categories",
        "financial_categories",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_financial_categories_parent_id_financial_categories",
        "financial_categories",
        type_="foreignkey",
    )
    op.drop_index("ix_financial_categories_parent_id", table_name="financial_categories")
    op.drop_column("financial_categories", "parent_id")
