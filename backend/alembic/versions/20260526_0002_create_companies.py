"""create companies

Revision ID: 20260526_0002
Revises: 20260525_0001
Create Date: 2026-05-26 00:02:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260526_0002"
down_revision: str | None = "20260525_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
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
    )

    op.execute(
        """
        INSERT INTO companies (id, name)
        SELECT DISTINCT
            users.company_id,
            'Empresa ' || substring(users.company_id::text from 1 for 8)
        FROM users
        WHERE users.company_id IS NOT NULL
        """
    )

    op.create_foreign_key(
        "fk_users_company_id_companies",
        "users",
        "companies",
        ["company_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_company_id_companies", "users", type_="foreignkey")
    op.drop_table("companies")
