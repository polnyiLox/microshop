from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BalanceOperation(Base):
    """Audit an idempotent credit or debit applied to a user balance."""

    __tablename__ = "balance_operations"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    reference: Mapped[str] = mapped_column(unique=True, index=True)
    amount_delta: Mapped[int]
    balance_after: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint("amount_delta != 0", name="ck_balance_operations_delta_non_zero"),
        CheckConstraint("balance_after >= 0", name="ck_balance_operations_balance_non_negative"),
    )
