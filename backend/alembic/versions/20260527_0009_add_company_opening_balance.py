"""add company opening balance

Revision ID: 20260527_0009
Revises: 20260526_0008
Create Date: 2026-05-27 00:09:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260527_0009"
down_revision: str | None = "20260526_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column(
            "opening_balance",
            sa.Numeric(14, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
    )
    op.add_column(
        "companies",
        sa.Column("opening_balance_date", sa.Date(), nullable=True),
    )
    op.alter_column("companies", "opening_balance", server_default=None)


def downgrade() -> None:
    op.drop_column("companies", "opening_balance_date")
    op.drop_column("companies", "opening_balance")
