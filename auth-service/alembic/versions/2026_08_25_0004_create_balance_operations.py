"""create balance operations

Revision ID: e4a1c7d9b305
Revises: d3f0a4b8c219
Create Date: 2026-08-25 00:04:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e4a1c7d9b305"
down_revision: Union[str, Sequence[str], None] = "d3f0a4b8c219"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "balance_operations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("amount_delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount_delta != 0",
            name="ck_balance_operations_delta_non_zero",
        ),
        sa.CheckConstraint(
            "balance_after >= 0",
            name="ck_balance_operations_balance_non_negative",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_balance_operations_reference",
        "balance_operations",
        ["reference"],
        unique=True,
    )
    op.create_index(
        "ix_balance_operations_user_id",
        "balance_operations",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_balance_operations_user_id", table_name="balance_operations")
    op.drop_index("ix_balance_operations_reference", table_name="balance_operations")
    op.drop_table("balance_operations")
