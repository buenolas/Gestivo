"""create import batches

Revision ID: 20260526_0006
Revises: 20260526_0005
Create Date: 2026-05-26 00:06:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260526_0006"
down_revision: str | None = "20260526_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    file_type = postgresql.ENUM(
        "csv",
        "xlsx",
        name="import_batch_file_type",
        create_type=False,
    )
    batch_status = postgresql.ENUM(
        "uploaded",
        "validated",
        "confirmed",
        "failed",
        name="import_batch_status",
        create_type=False,
    )
    file_type.create(op.get_bind(), checkfirst=True)
    batch_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", file_type, nullable=False),
        sa.Column("status", batch_status, nullable=False),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("preview_rows", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_rows", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "validation_errors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "duplicate_warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_import_batches_company_id_companies",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_import_batches_created_by_users",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by"],
            ["users.id"],
            name="fk_import_batches_confirmed_by_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_import_batches_company_id"), "import_batches", ["company_id"])

    op.add_column(
        "financial_transactions",
        sa.Column(
            "source",
            sa.String(length=40),
            nullable=False,
            server_default="manual",
        ),
    )
    op.add_column(
        "financial_transactions",
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_financial_transactions_import_batch_id_import_batches",
        "financial_transactions",
        "import_batches",
        ["import_batch_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_financial_transactions_import_batch_id"),
        "financial_transactions",
        ["import_batch_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_financial_transactions_import_batch_id"),
        table_name="financial_transactions",
    )
    op.drop_constraint(
        "fk_financial_transactions_import_batch_id_import_batches",
        "financial_transactions",
        type_="foreignkey",
    )
    op.drop_column("financial_transactions", "import_batch_id")
    op.drop_column("financial_transactions", "source")
    op.drop_index(op.f("ix_import_batches_company_id"), table_name="import_batches")
    op.drop_table("import_batches")
    postgresql.ENUM(name="import_batch_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="import_batch_file_type").drop(op.get_bind(), checkfirst=True)
