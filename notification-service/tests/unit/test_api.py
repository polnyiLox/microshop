from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.routers.v1.notification import get_notifications, require_notification_owner
from app.enums import NotificationStatusEnum
from app.exceptions import NotificationNotFoundError


@pytest.mark.asyncio
async def test_list_rejects_another_user() -> None:
    service = AsyncMock()

    with pytest.raises(NotificationNotFoundError):
        await get_notifications("other-user", "user-id", service)

    service.get_notifications_by_user_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_owner_dependency_hides_foreign_notification() -> None:
    service = AsyncMock()
    service.get_notification_by_id.return_value = SimpleNamespace(user_id="other-user")

    with pytest.raises(NotificationNotFoundError):
        await require_notification_owner("notification-id", "user-id", service)
