from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import RedisCache
from app.core.config import settings
from app.db.session import get_session
from app.repositories import NotificationRepository
from app.services import NotificationService
from app.websocket import notification_connection_manager


async def get_current_user_id(
    x_user_id: str = Header(alias="X-User-ID"),
) -> str:
    return x_user_id


redis_cache = RedisCache(settings=settings.redis)


def build_notification_service(session: AsyncSession) -> NotificationService:
    return NotificationService(
        notification_repo=NotificationRepository(session),
        session=session,
        connection_manager=notification_connection_manager,
        settings=settings,
        redis_cache=redis_cache
    )


async def get_notification_repo(
        session: AsyncSession = Depends(get_session),
) -> NotificationRepository:
    return NotificationRepository(session)


async def get_notification_service(
        session: AsyncSession = Depends(get_session),
) -> NotificationService:
    return build_notification_service(session)
