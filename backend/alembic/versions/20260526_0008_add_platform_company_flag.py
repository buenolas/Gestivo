"""add platform company flag

Revision ID: 20260526_0008
Revises: 20260526_0007
Create Date: 2026-05-26 00:08:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260526_0008"
down_revision: str | None = "20260526_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column(
            "is_platform_company",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column("companies", "is_platform_company", server_default=None)


def downgrade() -> None:
    op.drop_column("companies", "is_platform_company")
