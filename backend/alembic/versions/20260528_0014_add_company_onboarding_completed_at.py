"""add company onboarding completed at

Revision ID: 20260528_0014
Revises: 20260528_0013
Create Date: 2026-05-28 00:14:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260528_0014"
down_revision: str | None = "20260528_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE companies
        SET onboarding_completed_at = COALESCE(updated_at, created_at, now())
        WHERE is_platform_company = true OR name <> 'Configurar empresa'
        """
    )


def downgrade() -> None:
    op.drop_column("companies", "onboarding_completed_at")
