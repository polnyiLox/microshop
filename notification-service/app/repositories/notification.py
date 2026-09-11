from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all_by_user_id(self, user_id: str) -> list[Notification]:
        query = (select(Notification).where(Notification.user_id == user_id)
                 .order_by(Notification.created_at.desc()))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, notification_id: str) -> Notification | None:
        query = select(Notification).where(Notification.id == notification_id)
        result = await self._session.scalar(query)
        return result

    async def create(self, message: dict, user_id: str) -> Notification:
        new_notification = Notification(
            message=message,
            user_id=user_id
        )
        self._session.add(new_notification)
        await self._session.flush()
        return new_notification

    async def update(self, notification: Notification, **update_data) -> Notification:
        for key, value in update_data.items():
            setattr(notification, key, value)
        await self._session.flush()
        return notification

    async def delete(self, notification: Notification) -> None:
        await self._session.delete(notification)
        await self._session.flush()
