from app.enums import NotificationStatusEnum

from .base import AppError


class NotificationNotFoundError(AppError):
    detail: str = "Notification not found"
    status_code: int = 404


class ForbiddenChangeNotificationStatusError(AppError):
    def __init__(
            self,
            status_from: NotificationStatusEnum,
            status_to: NotificationStatusEnum,
    ):
        self.status_code = 403
        self.detail = f"Forbidden change notification status from {status_from.value} to {status_to.value}"