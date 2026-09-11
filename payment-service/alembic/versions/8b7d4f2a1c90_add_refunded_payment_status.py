"""add refunded payment status

Revision ID: 8b7d4f2a1c90
Revises: 4a9c7d2e1b60
Create Date: 2026-08-23 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "8b7d4f2a1c90"
down_revision: Union[str, Sequence[str], None] = "4a9c7d2e1b60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE payment_status ADD VALUE IF NOT EXISTS 'REFUNDED'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE payments SET status = 'SUCCEEDED' WHERE status = 'REFUNDED'"
    )
    op.execute("ALTER TYPE payment_status RENAME TO payment_status_old")

    payment_status = sa.Enum(
        "PENDING",
        "PROCESSING",
        "SUCCEEDED",
        "FAILED",
        "CANCELLED",
        name="payment_status",
    )
    payment_status.create(op.get_bind())

    op.execute(
        "ALTER TABLE payments ALTER COLUMN status "
        "TYPE payment_status USING status::text::payment_status"
    )
    op.execute("DROP TYPE payment_status_old")
