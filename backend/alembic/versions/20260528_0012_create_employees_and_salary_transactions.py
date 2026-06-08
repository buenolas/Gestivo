"""create employees and salary transaction links

Revision ID: 20260528_0012
Revises: 20260527_0011
Create Date: 2026-05-28 00:12:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260528_0012"
down_revision: str | None = "20260527_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    employee_status = postgresql.ENUM(
        "active",
        "inactive",
        "ended",
        name="employee_status",
        create_type=False,
    )
    employee_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("position", sa.String(length=120), nullable=True),
        sa.Column("salary_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("contract_start_date", sa.Date(), nullable=False),
        sa.Column("contract_end_date", sa.Date(), nullable=True),
        sa.Column("status", employee_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
            name="fk_employees_company_id_companies",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("salary_amount > 0", name="ck_employees_salary_amount_positive"),
    )
    op.create_index(op.f("ix_employees_company_id"), "employees", ["company_id"], unique=False)
    op.create_index(
        "ix_employees_company_status",
        "employees",
        ["company_id", "status"],
        unique=False,
    )

    op.add_column(
        "financial_transactions",
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "financial_transactions",
        sa.Column("reference_month", sa.Date(), nullable=True),
    )
    op.create_foreign_key(
        "fk_financial_transactions_employee_id_employees",
        "financial_transactions",
        "employees",
        ["employee_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_financial_transactions_employee_id"),
        "financial_transactions",
        ["employee_id"],
        unique=False,
    )
    op.create_index(
        "uq_salary_transaction_employee_month",
        "financial_transactions",
        ["company_id", "employee_id", "reference_month", "source"],
        unique=True,
        postgresql_where=sa.text("source = 'employee_salary'"),
    )


def downgrade() -> None:
    op.drop_index("uq_salary_transaction_employee_month", table_name="financial_transactions")
    op.drop_index(
        op.f("ix_financial_transactions_employee_id"),
        table_name="financial_transactions",
    )
    op.drop_constraint(
        "fk_financial_transactions_employee_id_employees",
        "financial_transactions",
        type_="foreignkey",
    )
    op.drop_column("financial_transactions", "reference_month")
    op.drop_column("financial_transactions", "employee_id")

    op.drop_index("ix_employees_company_status", table_name="employees")
    op.drop_index(op.f("ix_employees_company_id"), table_name="employees")
    op.drop_table("employees")
    postgresql.ENUM(name="employee_status").drop(op.get_bind(), checkfirst=True)
