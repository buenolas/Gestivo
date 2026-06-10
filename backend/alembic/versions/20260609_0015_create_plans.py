"""create platform plans

Revision ID: 20260609_0015
Revises: 20260528_0014
Create Date: 2026-06-09 00:15:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260609_0015"
down_revision: str | None = "20260528_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    billing_cycle = postgresql.ENUM(
        "monthly",
        "semiannual",
        "annual",
        name="billing_cycle",
        create_type=False,
    )
    billing_cycle.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=40), nullable=False),
        sa.Column("billing_cycle", billing_cycle, nullable=False),
        sa.Column("duration_months", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_plans_slug"), "plans", ["slug"], unique=True)

    op.execute(
        """
        INSERT INTO plans (id, name, slug, billing_cycle, duration_months, price, is_active, description)
        VALUES
            ('00000000-0000-0000-0000-000000000101', 'Mensal', 'monthly', 'monthly', 1, 0, true, 'Plano mensal da plataforma.'),
            ('00000000-0000-0000-0000-000000000102', 'Semestral', 'semiannual', 'semiannual', 6, 0, true, 'Plano semestral da plataforma.'),
            ('00000000-0000-0000-0000-000000000103', 'Anual', 'annual', 'annual', 12, 0, true, 'Plano anual da plataforma.')
        ON CONFLICT (slug) DO UPDATE
        SET
            name = EXCLUDED.name,
            billing_cycle = EXCLUDED.billing_cycle,
            duration_months = EXCLUDED.duration_months,
            updated_at = now()
        """
    )

    op.add_column("companies", sa.Column("current_plan_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_companies_current_plan_id"), "companies", ["current_plan_id"])
    op.create_foreign_key(
        "fk_companies_current_plan_id_plans",
        "companies",
        "plans",
        ["current_plan_id"],
        ["id"],
    )

    op.add_column("manual_payments", sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("manual_payments", sa.Column("plan_slug", sa.String(length=40), nullable=True))
    op.add_column("manual_payments", sa.Column("billing_cycle", billing_cycle, nullable=True))
    op.add_column("manual_payments", sa.Column("duration_months", sa.Integer(), nullable=True))
    op.add_column("manual_payments", sa.Column("price_at_payment", sa.Numeric(14, 2), nullable=True))
    op.create_index(op.f("ix_manual_payments_plan_id"), "manual_payments", ["plan_id"])
    op.create_foreign_key(
        "fk_manual_payments_plan_id_plans",
        "manual_payments",
        "plans",
        ["plan_id"],
        ["id"],
    )

    op.alter_column("plans", "price", server_default=None)
    op.alter_column("plans", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_manual_payments_plan_id_plans", "manual_payments", type_="foreignkey")
    op.drop_index(op.f("ix_manual_payments_plan_id"), table_name="manual_payments")
    op.drop_column("manual_payments", "price_at_payment")
    op.drop_column("manual_payments", "duration_months")
    op.drop_column("manual_payments", "billing_cycle")
    op.drop_column("manual_payments", "plan_slug")
    op.drop_column("manual_payments", "plan_id")

    op.drop_constraint("fk_companies_current_plan_id_plans", "companies", type_="foreignkey")
    op.drop_index(op.f("ix_companies_current_plan_id"), table_name="companies")
    op.drop_column("companies", "current_plan_id")

    op.drop_index(op.f("ix_plans_slug"), table_name="plans")
    op.drop_table("plans")
    postgresql.ENUM(name="billing_cycle").drop(op.get_bind(), checkfirst=True)
