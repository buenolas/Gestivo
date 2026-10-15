"""replace billing cycles with monthly plan tiers

Revision ID: 20261014_0023
Revises: 20260625_0022
Create Date: 2026-10-14 00:23:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20261014_0023"
down_revision: str | None = "20260625_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None

BASIC_FEATURES = [
    "dashboard",
    "transactions",
    "payables",
    "receivables",
    "categories",
    "contacts",
]
ALL_FEATURES = [
    "dashboard",
    "assistant",
    "cashflow",
    "product_outputs",
    "transactions",
    "payables",
    "receivables",
    "categories",
    "imports",
    "employees",
    "users",
    "contacts",
]


def _json(value: list[str]) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def upgrade() -> None:
    op.add_column(
        "plans",
        sa.Column(
            "feature_codes",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )
    op.add_column("plans", sa.Column("ai_daily_limit", sa.Integer(), nullable=True))
    op.alter_column("plans", "feature_codes", server_default=None)

    op.execute("UPDATE plans SET slug = 'basic' WHERE slug = 'monthly'")
    op.execute(
        sa.text(
            """
            UPDATE plans
            SET name = 'Básico',
                billing_cycle = 'monthly',
                duration_months = 1,
                price = 10.90,
                is_active = true,
                description = 'Lançamentos, contas a pagar e a receber, visão geral, categorias e contatos.',
                feature_codes = CAST(:features AS JSON),
                ai_daily_limit = 0,
                updated_at = now()
            WHERE slug = 'basic'
            """
        ).bindparams(features=_json(BASIC_FEATURES))
    )

    op.execute(
        sa.text(
            """
            UPDATE plans
            SET is_active = false,
                feature_codes = CAST(:features AS JSON),
                ai_daily_limit = NULL,
                updated_at = now()
            WHERE slug IN ('semiannual', 'annual')
            """
        ).bindparams(features=_json(ALL_FEATURES))
    )

    for plan_id, name, slug, price, ai_limit, description in (
        (
            "00000000-0000-0000-0000-000000000104",
            "Intermediário",
            "intermediate",
            "21.90",
            2,
            "Todos os recursos, com até 2 interações com a IA por dia.",
        ),
        (
            "00000000-0000-0000-0000-000000000105",
            "Avançado",
            "advanced",
            "29.90",
            10,
            "Todos os recursos, com até 10 interações com a IA por dia.",
        ),
        (
            "00000000-0000-0000-0000-000000000106",
            "Pro",
            "pro",
            "39.90",
            None,
            "Todos os recursos, com interações ilimitadas com a IA.",
        ),
    ):
        op.execute(
            sa.text(
                """
                INSERT INTO plans (
                    id, name, slug, billing_cycle, duration_months, price,
                    is_active, description, feature_codes, ai_daily_limit,
                    created_at, updated_at
                )
                VALUES (
                    CAST(:id AS UUID), :name, :slug, 'monthly', 1,
                    CAST(:price AS NUMERIC(14, 2)),
                    true, :description, CAST(:features AS JSON), :ai_limit, now(), now()
                )
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    billing_cycle = EXCLUDED.billing_cycle,
                    duration_months = 1,
                    price = EXCLUDED.price,
                    is_active = true,
                    description = EXCLUDED.description,
                    feature_codes = EXCLUDED.feature_codes,
                    ai_daily_limit = EXCLUDED.ai_daily_limit,
                    updated_at = now()
                """
            ).bindparams(
                id=plan_id,
                name=name,
                slug=slug,
                price=price,
                description=description,
                features=_json(ALL_FEATURES),
                ai_limit=ai_limit,
            )
        )

    op.execute("ALTER TYPE usage_event_type ADD VALUE IF NOT EXISTS 'assistant_interaction'")


def downgrade() -> None:
    op.execute(
        "DELETE FROM plans WHERE slug IN ('intermediate', 'advanced', 'pro')"
    )
    op.execute(
        "UPDATE plans SET slug = 'monthly', name = 'Mensal', price = 0, is_active = true "
        "WHERE slug = 'basic'"
    )
    op.execute("UPDATE plans SET is_active = true WHERE slug IN ('semiannual', 'annual')")
    op.drop_column("plans", "ai_daily_limit")
    op.drop_column("plans", "feature_codes")
