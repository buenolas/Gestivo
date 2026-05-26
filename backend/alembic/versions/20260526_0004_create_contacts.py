"""create contacts

Revision ID: 20260526_0004
Revises: 20260526_0003
Create Date: 2026-05-26 00:04:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260526_0004"
down_revision: str | None = "20260526_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    contact_type = postgresql.ENUM(
        "customer",
        "supplier",
        "both",
        name="contact_type",
        create_type=False,
    )
    contact_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("type", contact_type, nullable=False),
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
            name="fk_contacts_company_id_companies",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contacts_company_id"), "contacts", ["company_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_contacts_company_id"), table_name="contacts")
    op.drop_table("contacts")
    postgresql.ENUM(name="contact_type").drop(op.get_bind(), checkfirst=True)
