"""add user password change flag

Revision ID: 20260611_0018
Revises: 20260610_0017
Create Date: 2026-06-11 00:18:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260611_0018"
down_revision: str | None = "20260610_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("users", "must_change_password", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
