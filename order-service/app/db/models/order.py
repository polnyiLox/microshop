from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, func, Enum as SqlalchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import OrderStatusEnum

from .base import Base

if TYPE_CHECKING:
    from .order_item import OrderItem


class Order(Base):
    __tablename__ = "orders"

    user_id: Mapped[str]
    status: Mapped[OrderStatusEnum] = mapped_column(
        SqlalchemyEnum(OrderStatusEnum),
        default=OrderStatusEnum.CREATED
    )
    total_amount: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )