import json
from json import JSONDecodeError
import logging

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import RedisCache
from app.core.config import Settings
from app.db.models import Notification
from app.enums import NotificationStatusEnum
from app.exceptions import NotificationNotFoundError, ForbiddenChangeNotificationStatusError
from app.repositories import NotificationRepository
from app.schemas import NotificationRead
from app.websocket import NotificationConnectionManager


logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
            self,
            session: AsyncSession,
            notification_repo: NotificationRepository,
            connection_manager: NotificationConnectionManager,
            redis_cache: RedisCache,
            settings: Settings,
    ) -> None:
        self._session = session
        self._notification_repo = notification_repo
        self._connection_manager = connection_manager
        self._redis_cache = redis_cache
        self._settings = settings

    async def _invalidate_notification(self, notification: Notification) -> None:
        await self._redis_cache.delete(
            notification.id,
            self._redis_cache.create_user_notifications_key(notification.user_id),
        )

    async def _get_existing_notification(self, notification_id: str) -> Notification:
        notification = await self._notification_repo.get_by_id(notification_id)
        if notification is None:
            logger.warning("Notification not found notification_id=%s", notification_id)
            raise NotificationNotFoundError()
        return notification

    async def get_notification_by_id(self, notification_id: str) -> NotificationRead:
        logger.debug("Reading notification notification_id=%s", notification_id)
        # Идем в кэш
        cached_notification = await self._redis_cache.get(
            key=notification_id
        )
        if cached_notification is not None:
            logger.debug("Notification cache hit notification_id=%s", notification_id)
            try:
                return NotificationRead.model_validate_json(cached_notification)
            except ValidationError:
                logger.warning("Invalid cached notification notification_id=%s", notification_id)
                await self._redis_cache.delete(notification_id)
        else:
            logger.debug("Notification cache miss notification_id=%s", notification_id)

        notification_orm = await self._get_existing_notification(notification_id)
        notification_read = NotificationRead.model_validate(notification_orm)
        # Записываем в кэш
        await self._redis_cache.set(
            key=notification_id,
            value=json.dumps(notification_read.model_dump(mode="json")),
            ttl_seconds=self._settings.redis.ttl_seconds
        )
        return notification_read

    async def get_notifications_by_user_id(self, user_id: str) -> list[NotificationRead]:
        logger.debug("Reading user notifications user_id=%s", user_id)
        # Читаем из кэша
        user_notifications_key = self._redis_cache.create_user_notifications_key(
            user_id=user_id
        )
        cached_notifications = await self._redis_cache.get(
            key=user_notifications_key
        )
        if cached_notifications is not None:
            logger.debug("User notifications cache hit user_id=%s", user_id)
            try:
                notifications_json = json.loads(cached_notifications)
                return [NotificationRead.model_validate(notification) for notification in notifications_json]
            except (JSONDecodeError, ValidationError, TypeError):
                logger.warning("Invalid cached notification list user_id=%s", user_id)
                await self._redis_cache.delete(user_notifications_key)
        else:
            logger.debug("User notifications cache miss user_id=%s", user_id)

        notifications = await self._notification_repo.get_all_by_user_id(user_id)
        notifications_read = [NotificationRead.model_validate(notification) for notification in notifications]
        # Записываем в кэш
        await self._redis_cache.set(
            key=user_notifications_key,
            value=json.dumps([notification.model_dump(mode="json") for notification in notifications_read]),
            ttl_seconds=self._settings.redis.ttl_seconds
        )
        return notifications_read

    async def create_notification(self, user_id: str, message: dict) -> NotificationRead:
        logger.info("Starting notification creation user_id=%s", user_id)
        notification = await self._notification_repo.create(
            user_id=user_id,
            message=message
        )
        await self._session.commit()
        await self._redis_cache.delete(
            self._redis_cache.create_user_notifications_key(user_id)
        )

        notification_read = NotificationRead.model_validate(notification)
        await self._connection_manager.send_to_user(
            user_id=user_id,
            notification=notification_read.model_dump(mode="json"),
        )
        logger.info(
            "Notification created notification_id=%s user_id=%s",
            notification.id,
            user_id,
        )
        return notification_read

    async def update_notification(
            self,
            notification_id: str,
            message: dict | None = None,
            status: NotificationStatusEnum | None = None
    ) -> NotificationRead:
        logger.info("Starting notification update notification_id=%s", notification_id)
        notification = await self._get_existing_notification(notification_id)
        update_data = {}

        if message is not None:
            update_data["message"] = message
        if status is not None:
            if not notification.status.can_transition_to(status):
                logger.warning(
                    "Notification status transition rejected notification_id=%s from=%s to=%s",
                    notification_id,
                    notification.status,
                    status,
                )
                raise ForbiddenChangeNotificationStatusError(
                    status_from=notification.status,
                    status_to=status
                )
            update_data["status"] = status

        await self._notification_repo.update(notification, **update_data)
        await self._session.commit()
        await self._invalidate_notification(notification)
        logger.info("Notification updated notification_id=%s", notification_id)

        return NotificationRead.model_validate(notification)

    async def delete_notification(self, notification_id: str) -> None:
        logger.info("Starting notification deletion notification_id=%s", notification_id)
        notification = await self._get_existing_notification(notification_id)

        await self._notification_repo.delete(notification)
        await self._session.commit()
        await self._invalidate_notification(notification)
        logger.info("Notification deleted notification_id=%s", notification_id)
