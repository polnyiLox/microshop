from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import UserRole

from .base import Base


class User(Base):
    __tablename__ = 'users'

    email: Mapped[str] = mapped_column(
        unique=True,
        index=True
    )
    phone_number: Mapped[str] = mapped_column(
        unique=True,
        index=True
    )
    balance: Mapped[int] = mapped_column(
        default=0,
        server_default="0",
    )
    hashed_password: Mapped[str]
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            native_enum=False,
            values_callable=lambda roles: [role.value for role in roles],
        ),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "balance >= 0",
            name="ck_users_balance_non_negative",
        ),
    )
