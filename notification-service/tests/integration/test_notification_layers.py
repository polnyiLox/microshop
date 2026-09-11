from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import NotificationStatusEnum
from app.exceptions import ForbiddenChangeNotificationStatusError
from app.repositories import NotificationRepository
from app.services import NotificationService


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_repository_orders_notifications_newest_first(session: AsyncSession) -> None:
    repository = NotificationRepository(session)
    first = await repository.create({"index": 1}, "user-id")
    second = await repository.create({"index": 2}, "user-id")
    await session.flush()

    results = await repository.get_all_by_user_id("user-id")

    assert {item.id for item in results} == {first.id, second.id}
    assert await repository.get_by_id(first.id) is first


async def test_service_persists_and_updates_notification(session: AsyncSession) -> None:
    repository = NotificationRepository(session)
    manager = AsyncMock()
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_user_notifications_key = Mock(
        side_effect=lambda user_id: f"user:{user_id}"
    )
    settings = SimpleNamespace(redis=SimpleNamespace(ttl_seconds=60))
    service = NotificationService(session, repository, manager, cache, settings)

    created = await service.create_notification("user-id", {"text": "hello"})
    updated = await service.update_notification(
        created.id,
        status=NotificationStatusEnum.SENT,
    )

    assert updated.status == NotificationStatusEnum.SENT
    assert (await repository.get_by_id(created.id)).status == NotificationStatusEnum.SENT
    manager.send_to_user.assert_awaited_once()


async def test_service_rejects_invalid_persisted_status_transition(
    session: AsyncSession,
) -> None:
    repository = NotificationRepository(session)
    cache = AsyncMock()
    cache.create_user_notifications_key = Mock(
        side_effect=lambda user_id: f"user:{user_id}",
    )
    service = NotificationService(
        session,
        repository,
        AsyncMock(),
        cache,
        SimpleNamespace(redis=SimpleNamespace(ttl_seconds=60)),
    )
    created = await service.create_notification(
        "status-user",
        {"text": "status"},
    )
    await service.update_notification(
        created.id,
        status=NotificationStatusEnum.READ,
    )

    with pytest.raises(ForbiddenChangeNotificationStatusError):
        await service.update_notification(
            created.id,
            status=NotificationStatusEnum.SENT,
        )

    stored = await repository.get_by_id(created.id)
    assert stored is not None
    assert stored.status == NotificationStatusEnum.READ
