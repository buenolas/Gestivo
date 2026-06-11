"""add admin financial dashboard fields

Revision ID: 20260610_0017
Revises: 20260609_0016
Create Date: 2026-06-10 00:17:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260610_0017"
down_revision: str | None = "20260609_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    payment_status = postgresql.ENUM(
        "paid",
        "pending",
        "canceled",
        "refunded",
        name="payment_status",
        create_type=False,
    )
    payment_status.create(op.get_bind(), checkfirst=True)

    op.add_column("companies", sa.Column("subscription_price", sa.Numeric(14, 2), nullable=True))
    op.add_column("companies", sa.Column("subscription_duration_months", sa.Integer(), nullable=True))
    op.add_column(
        "companies",
        sa.Column("subscription_period_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE companies AS c
        SET
            subscription_price = p.price,
            subscription_duration_months = p.duration_months
        FROM plans AS p
        WHERE c.current_plan_id = p.id
        """
    )
    op.execute(
        """
        UPDATE companies
        SET subscription_period_start = subscription_valid_until - interval '1 month'
        WHERE subscription_valid_until IS NOT NULL
        """
    )

    op.add_column(
        "manual_payments",
        sa.Column("status", payment_status, nullable=False, server_default="paid"),
    )
    op.add_column(
        "manual_payments",
        sa.Column("payment_method", sa.String(length=40), nullable=False, server_default="manual"),
    )
    op.add_column(
        "manual_payments",
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE manual_payments SET due_date = paid_at")
    op.alter_column("manual_payments", "paid_at", nullable=True)
    op.create_index(op.f("ix_manual_payments_status"), "manual_payments", ["status"])
    op.create_index(op.f("ix_manual_payments_due_date"), "manual_payments", ["due_date"])
    op.alter_column("manual_payments", "status", server_default=None)
    op.alter_column("manual_payments", "payment_method", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_manual_payments_due_date"), table_name="manual_payments")
    op.drop_index(op.f("ix_manual_payments_status"), table_name="manual_payments")
    op.execute("UPDATE manual_payments SET paid_at = due_date WHERE paid_at IS NULL")
    op.alter_column("manual_payments", "paid_at", nullable=False)
    op.drop_column("manual_payments", "due_date")
    op.drop_column("manual_payments", "payment_method")
    op.drop_column("manual_payments", "status")
    op.drop_column("companies", "subscription_period_start")
    op.drop_column("companies", "subscription_duration_months")
    op.drop_column("companies", "subscription_price")
    postgresql.ENUM(name="payment_status").drop(op.get_bind(), checkfirst=True)
