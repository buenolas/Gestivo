"""create subscriptions

Revision ID: 20260526_0007
Revises: 20260526_0006
Create Date: 2026-05-26 00:07:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260526_0007"
down_revision: str | None = "20260526_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    subscription_status = postgresql.ENUM(
        "trialing",
        "active",
        "pending_payment",
        "canceled",
        "blocked",
        name="subscription_status",
        create_type=False,
    )
    subscription_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "companies",
        sa.Column(
            "subscription_status",
            subscription_status,
            nullable=False,
            server_default="trialing",
        ),
    )
    op.add_column(
        "companies",
        sa.Column(
            "trial_ends_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "companies",
        sa.Column(
            "subscription_valid_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.execute("UPDATE companies SET trial_ends_at = now() + interval '30 days'")
    op.alter_column("companies", "trial_ends_at", nullable=False)

    op.create_table(
        "manual_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_manual_payments_company_id_companies",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_manual_payments_created_by_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_manual_payments_company_id"), "manual_payments", ["company_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_manual_payments_company_id"), table_name="manual_payments")
    op.drop_table("manual_payments")
    op.drop_column("companies", "subscription_valid_until")
    op.drop_column("companies", "trial_ends_at")
    op.drop_column("companies", "subscription_status")
    postgresql.ENUM(name="subscription_status").drop(op.get_bind(), checkfirst=True)
