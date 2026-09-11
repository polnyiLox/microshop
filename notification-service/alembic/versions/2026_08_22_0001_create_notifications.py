"""create notifications table

Revision ID: 7f2a6c9d4e10
Revises:
Create Date: 2026-08-22 00:01:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "7f2a6c9d4e10"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    notification_status = sa.Enum(
        "CREATED",
        "SENT",
        "DELIVERED",
        "READ",
        "FAILED",
        "CANCELED",
        name="notification_status",
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("message", sa.JSON(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("status", notification_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    sa.Enum(name="notification_status").drop(op.get_bind(), checkfirst=True)
