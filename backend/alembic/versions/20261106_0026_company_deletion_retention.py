"""add 30-day company deletion retention marker

Revision ID: 20261106_0026
Revises: 20261015_0025
Create Date: 2026-11-06 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20261106_0026"
down_revision: str | None = "20261015_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_companies_deletion_requested_at",
        "companies",
        ["deletion_requested_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_companies_deletion_requested_at", table_name="companies")
    op.drop_column("companies", "deletion_requested_at")
