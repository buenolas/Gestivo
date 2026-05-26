"""create financial categories

Revision ID: 20260526_0003
Revises: 20260526_0002
Create Date: 2026-05-26 00:03:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260526_0003"
down_revision: str | None = "20260526_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    financial_category_type = postgresql.ENUM(
        "income",
        "expense",
        "both",
        name="financial_category_type",
        create_type=False,
    )
    financial_category_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "financial_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("type", financial_category_type, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
            name="fk_financial_categories_company_id_companies",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_financial_categories_company_id"),
        "financial_categories",
        ["company_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_financial_categories_company_id_name_lower
        ON financial_categories (company_id, lower(name))
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_financial_categories_company_id_name_lower")
    op.drop_index(
        op.f("ix_financial_categories_company_id"),
        table_name="financial_categories",
    )
    op.drop_table("financial_categories")
    postgresql.ENUM(name="financial_category_type").drop(op.get_bind(), checkfirst=True)
