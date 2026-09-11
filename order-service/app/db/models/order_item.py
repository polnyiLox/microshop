from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .order import Order


class OrderItem(Base):
    __tablename__ = "order_items"

    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.id")
    )

    product_id: Mapped[str]
    seller_id: Mapped[str] = mapped_column(index=True)
    product_name: Mapped[str]
    quantity: Mapped[int]
    unit_price: Mapped[int]

    order: Mapped[Order] = relationship(
        back_populates="items"
    )
