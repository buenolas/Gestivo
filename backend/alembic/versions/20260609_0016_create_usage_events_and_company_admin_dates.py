"""create usage events and company admin dates

Revision ID: 20260609_0016
Revises: 20260609_0015
Create Date: 2026-06-09 00:16:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260609_0016"
down_revision: str | None = "20260609_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    usage_event_type = postgresql.ENUM(
        "login",
        "spreadsheet_import",
        "financial_entry_created",
        "subscription_renewed",
        "subscription_blocked",
        "subscription_unblocked",
        "subscription_canceled",
        "subscription_reactivated",
        "plan_changed",
        name="usage_event_type",
        create_type=False,
    )
    usage_event_type.create(op.get_bind(), checkfirst=True)

    op.add_column("companies", sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("companies", sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", usage_event_type, nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_usage_events_company_id_companies",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_usage_events_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usage_events_company_id"), "usage_events", ["company_id"])
    op.create_index(op.f("ix_usage_events_user_id"), "usage_events", ["user_id"])
    op.create_index(op.f("ix_usage_events_event_type"), "usage_events", ["event_type"])
    op.create_index(op.f("ix_usage_events_created_at"), "usage_events", ["created_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_events_created_at"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_event_type"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_user_id"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_company_id"), table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_column("companies", "canceled_at")
    op.drop_column("companies", "blocked_at")
    postgresql.ENUM(name="usage_event_type").drop(op.get_bind(), checkfirst=True)
