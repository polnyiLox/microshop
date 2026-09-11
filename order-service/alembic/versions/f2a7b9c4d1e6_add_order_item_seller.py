"""add order item seller

Revision ID: f2a7b9c4d1e6
Revises: 8d4f1a7c2e90
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f2a7b9c4d1e6"
down_revision: Union[str, Sequence[str], None] = "8d4f1a7c2e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("seller_id", sa.String(), server_default="legacy", nullable=False),
    )
    op.create_index("ix_order_items_seller_id", "order_items", ["seller_id"])
    op.alter_column("order_items", "seller_id", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_order_items_seller_id", table_name="order_items")
    op.drop_column("order_items", "seller_id")
