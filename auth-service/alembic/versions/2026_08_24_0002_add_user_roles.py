"""add user roles

Revision ID: a71c8e245f90
Revises: 6c4e2a9f1b70
Create Date: 2026-08-24 13:50:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a71c8e245f90"
down_revision: Union[str, Sequence[str], None] = "6c4e2a9f1b70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=6),
            server_default="user",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('user', 'seller', 'admin')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
