from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user_id, get_notification_service
from app.exceptions import NotificationNotFoundError
from app.schemas import NotificationRead
from app.services import NotificationService

router = APIRouter(
    prefix="/notifications",
    tags=["Уведомления"],
)


async def require_notification_owner(
        notification_id: str,
        current_user_id: str = Depends(get_current_user_id),
        service: NotificationService = Depends(get_notification_service),
) -> str:
    notification = await service.get_notification_by_id(notification_id)
    if notification.user_id != current_user_id:
        raise NotificationNotFoundError()
    return current_user_id


@router.get("/users/{user_id}", response_model=list[NotificationRead])
async def get_notifications(
        user_id: str,
        current_user_id: str = Depends(get_current_user_id),
        service: NotificationService = Depends(get_notification_service),
) -> list[NotificationRead]:
    if user_id != current_user_id:
        raise NotificationNotFoundError()
    return await service.get_notifications_by_user_id(current_user_id)


@router.get("/{notification_id}", response_model=NotificationRead)
async def get_notification(
        notification_id: str,
        current_user_id: str = Depends(require_notification_owner),
        service: NotificationService = Depends(get_notification_service),
) -> NotificationRead:
    return await service.get_notification_by_id(notification_id)
