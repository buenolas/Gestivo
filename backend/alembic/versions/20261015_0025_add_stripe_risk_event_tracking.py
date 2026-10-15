"""add Stripe risk event tracking fields

Revision ID: 20261015_0025
Revises: 20261015_0024
Create Date: 2026-10-15 01:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261015_0025"
down_revision: str | None = "20261015_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "stripe_webhook_events",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "stripe_webhook_events",
        sa.Column("risk_object_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "stripe_webhook_events",
        sa.Column("risk_charge_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "stripe_webhook_events",
        sa.Column("risk_review_status", sa.String(length=24), nullable=True),
    )
    op.create_foreign_key(
        "fk_stripe_webhook_events_company_id_companies",
        "stripe_webhook_events",
        "companies",
        ["company_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_stripe_webhook_events_company_id",
        "stripe_webhook_events",
        ["company_id"],
    )
    op.create_index(
        "ix_stripe_webhook_events_risk_review_status",
        "stripe_webhook_events",
        ["risk_review_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_stripe_webhook_events_risk_review_status", table_name="stripe_webhook_events")
    op.drop_index("ix_stripe_webhook_events_company_id", table_name="stripe_webhook_events")
    op.drop_constraint(
        "fk_stripe_webhook_events_company_id_companies",
        "stripe_webhook_events",
        type_="foreignkey",
    )
    op.drop_column("stripe_webhook_events", "risk_review_status")
    op.drop_column("stripe_webhook_events", "risk_charge_id")
    op.drop_column("stripe_webhook_events", "risk_object_id")
    op.drop_column("stripe_webhook_events", "company_id")
