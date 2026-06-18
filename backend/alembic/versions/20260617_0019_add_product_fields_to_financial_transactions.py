"""add product fields to financial transactions

Revision ID: 20260617_0019
Revises: 20260611_0018
Create Date: 2026-06-17 00:19:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260617_0019"
down_revision: str | None = "20260611_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "financial_transactions",
        sa.Column("product_name", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "financial_transactions",
        sa.Column("product_quantity", sa.Numeric(14, 3), nullable=True),
    )
    op.add_column(
        "financial_transactions",
        sa.Column("product_unit", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("financial_transactions", "product_unit")
    op.drop_column("financial_transactions", "product_quantity")
    op.drop_column("financial_transactions", "product_name")
