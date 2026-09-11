"""add waiting payment and failed order statuses

Revision ID: 8d4f1a7c2e90
Revises: 1b3f6e89a2d0
Create Date: 2026-08-21 00:02:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "8d4f1a7c2e90"
down_revision: Union[str, Sequence[str], None] = "1b3f6e89a2d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE orderstatusenum ADD VALUE IF NOT EXISTS 'WAITING_PAYMENT'")
    op.execute("ALTER TYPE orderstatusenum ADD VALUE IF NOT EXISTS 'FAILED'")


def downgrade() -> None:
    # PostgreSQL cannot safely remove enum values while rows may use them.
    pass
