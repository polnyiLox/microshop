"""add user balance

Revision ID: d3f0a4b8c219
Revises: a71c8e245f90
Create Date: 2026-08-25 00:03:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d3f0a4b8c219"
down_revision: Union[str, Sequence[str], None] = "a71c8e245f90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "balance",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_users_balance_non_negative",
        "users",
        "balance >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_users_balance_non_negative",
        "users",
        type_="check",
    )
    op.drop_column("users", "balance")
