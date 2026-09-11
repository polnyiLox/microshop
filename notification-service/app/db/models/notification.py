from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum as SqlAlchemyEnum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import NotificationStatusEnum

from .base import Base


class Notification(Base):
    __tablename__ = "notifications"

    message: Mapped[dict] = mapped_column(JSON)
    user_id: Mapped[str]
    status: Mapped[NotificationStatusEnum] = mapped_column(
        SqlAlchemyEnum(NotificationStatusEnum, name="notification_status"),
        default=NotificationStatusEnum.CREATED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
