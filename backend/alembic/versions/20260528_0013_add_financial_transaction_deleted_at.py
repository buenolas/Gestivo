"""add financial transaction deleted_at

Revision ID: 20260528_0013
Revises: 20260528_0012
Create Date: 2026-05-28 00:13:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260528_0013"
down_revision: str | None = "20260528_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "financial_transactions",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_financial_transactions_deleted_at"),
        "financial_transactions",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_financial_transactions_deleted_at"),
        table_name="financial_transactions",
    )
    op.drop_column("financial_transactions", "deleted_at")
