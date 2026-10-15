"""add Stripe Billing identifiers and webhook idempotency storage

Revision ID: 20261015_0024
Revises: 20261014_0023
Create Date: 2026-10-15 00:24:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20261015_0024"
down_revision: str | None = "20261014_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column("companies", sa.Column("stripe_subscription_id", sa.String(255), nullable=True))
    op.add_column("companies", sa.Column("stripe_subscription_status", sa.String(32), nullable=True))
    op.add_column(
        "companies",
        sa.Column("stripe_subscription_event_created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_companies_stripe_customer_id",
        "companies",
        ["stripe_customer_id"],
        unique=True,
    )
    op.create_index(
        "uq_companies_stripe_subscription_id",
        "companies",
        ["stripe_subscription_id"],
        unique=True,
    )
    op.create_table(
        "stripe_webhook_events",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("stripe_webhook_events")
    op.drop_index("uq_companies_stripe_subscription_id", table_name="companies")
    op.drop_index("uq_companies_stripe_customer_id", table_name="companies")
    op.drop_column("companies", "stripe_subscription_event_created_at")
    op.drop_column("companies", "stripe_subscription_status")
    op.drop_column("companies", "stripe_subscription_id")
    op.drop_column("companies", "stripe_customer_id")
