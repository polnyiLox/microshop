"""add product seller

Revision ID: c8f4a1d2e6b3
Revises: 5cdee5b20d86
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c8f4a1d2e6b3"
down_revision: Union[str, Sequence[str], None] = "5cdee5b20d86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("seller_id", sa.String(), server_default="legacy", nullable=False),
    )
    op.create_index("ix_products_seller_id", "products", ["seller_id"])
    op.alter_column("products", "seller_id", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_products_seller_id", table_name="products")
    op.drop_column("products", "seller_id")
