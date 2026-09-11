from datetime import datetime

from sqlalchemy import DateTime, Enum as SqlalchemyEnum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import PaymentStatusEnum

from .base import Base


class Payment(Base):
    __tablename__ = "payments"

    user_id: Mapped[str] = mapped_column(index=True)
    order_id: Mapped[str]
    status: Mapped[PaymentStatusEnum] = mapped_column(
        SqlalchemyEnum(PaymentStatusEnum, name="payment_status"),
        default=PaymentStatusEnum.PENDING,
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
