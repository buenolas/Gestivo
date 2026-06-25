"""add payment method to financial transactions

Revision ID: 20260625_0022
Revises: 20260618_0021
Create Date: 2026-06-25 00:22:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260625_0022"
down_revision: str | None = "20260618_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    payment_method = postgresql.ENUM(
        "credit",
        "debit",
        "pix",
        "boleto",
        "bank_transfer",
        "cash",
        name="financial_transaction_payment_method",
    )
    payment_method.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "financial_transactions",
        sa.Column("payment_method", payment_method, nullable=True),
    )
    op.create_index(
        op.f("ix_financial_transactions_payment_method"),
        "financial_transactions",
        ["payment_method"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_financial_transactions_payment_method"),
        table_name="financial_transactions",
    )
    op.drop_column("financial_transactions", "payment_method")
    postgresql.ENUM(name="financial_transaction_payment_method").drop(
        op.get_bind(),
        checkfirst=True,
    )
