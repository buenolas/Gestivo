"""create financial transactions

Revision ID: 20260526_0005
Revises: 20260526_0004
Create Date: 2026-05-26 00:05:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260526_0005"
down_revision: str | None = "20260526_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    transaction_type = postgresql.ENUM(
        "income",
        "expense",
        name="financial_transaction_type",
        create_type=False,
    )
    transaction_status = postgresql.ENUM(
        "pending",
        "settled",
        "canceled",
        name="financial_transaction_status",
        create_type=False,
    )
    transaction_type.create(op.get_bind(), checkfirst=True)
    transaction_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "financial_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("type", transaction_type, nullable=False),
        sa.Column("status", transaction_status, nullable=False),
        sa.Column("competence_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
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
            ["category_id"],
            ["financial_categories.id"],
            name="fk_financial_transactions_category_id_financial_categories",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_financial_transactions_company_id_companies",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name="fk_financial_transactions_contact_id_contacts",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_financial_transactions_created_by_users",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_financial_transactions_updated_by_users",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount > 0", name="ck_financial_transactions_amount_positive"),
    )
    op.create_index(
        op.f("ix_financial_transactions_company_id"),
        "financial_transactions",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_financial_transactions_category_id"),
        "financial_transactions",
        ["category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_financial_transactions_contact_id"),
        "financial_transactions",
        ["contact_id"],
        unique=False,
    )
    op.create_index(
        "ix_financial_transactions_company_competence_date",
        "financial_transactions",
        ["company_id", "competence_date"],
        unique=False,
    )
    op.create_index(
        "ix_financial_transactions_company_status",
        "financial_transactions",
        ["company_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_financial_transactions_company_status", table_name="financial_transactions")
    op.drop_index(
        "ix_financial_transactions_company_competence_date",
        table_name="financial_transactions",
    )
    op.drop_index(
        op.f("ix_financial_transactions_contact_id"),
        table_name="financial_transactions",
    )
    op.drop_index(
        op.f("ix_financial_transactions_category_id"),
        table_name="financial_transactions",
    )
    op.drop_index(
        op.f("ix_financial_transactions_company_id"),
        table_name="financial_transactions",
    )
    op.drop_table("financial_transactions")
    postgresql.ENUM(name="financial_transaction_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="financial_transaction_type").drop(op.get_bind(), checkfirst=True)
