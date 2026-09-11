"""store product image keys

Revision ID: 4a7c2e91b5d8
Revises: c8f4a1d2e6b3
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "4a7c2e91b5d8"
down_revision: Union[str, Sequence[str], None] = "c8f4a1d2e6b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "products",
        "image",
        new_column_name="image_key",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("UPDATE products SET image_key = '' WHERE image_key IS NULL")
    op.alter_column(
        "products",
        "image_key",
        new_column_name="image",
        existing_type=sa.String(),
        nullable=False,
        server_default="",
    )
    op.alter_column("products", "image", server_default=None)
