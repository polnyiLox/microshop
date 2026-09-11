from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.enums import NotificationStatusEnum
from app.exceptions import ForbiddenChangeNotificationStatusError, NotificationNotFoundError
from app.schemas import NotificationRead
from app.services import NotificationService


def notification(status: NotificationStatusEnum = NotificationStatusEnum.CREATED):
    return SimpleNamespace(
        id="notification-id",
        user_id="user-id",
        message={"text": "hello"},
        status=status,
        created_at=datetime.now(UTC),
    )


def build_service():
    session = AsyncMock()
    repository = AsyncMock()
    manager = AsyncMock()
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_user_notifications_key = Mock(
        side_effect=lambda user_id: f"user:{user_id}"
    )
    settings = SimpleNamespace(redis=SimpleNamespace(ttl_seconds=60))
    service = NotificationService(
        session,
        repository,
        manager,
        cache,
        settings,
    )
    return service, session, repository, manager, cache


@pytest.mark.asyncio
async def test_create_commits_before_sending_to_user() -> None:
    service, session, repository, manager, cache = build_service()
    repository.create.return_value = notification()

    result = await service.create_notification("user-id", {"text": "hello"})

    repository.create.assert_awaited_once_with(
        user_id="user-id",
        message={"text": "hello"},
    )
    session.commit.assert_awaited_once()
    manager.send_to_user.assert_awaited_once()
    cache.delete.assert_awaited_once_with("user:user-id")
    assert result.id == "notification-id"


@pytest.mark.asyncio
async def test_update_rejects_invalid_status_transition() -> None:
    service, session, repository, _, _ = build_service()
    repository.get_by_id.return_value = notification(NotificationStatusEnum.READ)

    with pytest.raises(ForbiddenChangeNotificationStatusError):
        await service.update_notification(
            "notification-id",
            status=NotificationStatusEnum.SENT,
        )

    repository.update.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_notification_is_reported() -> None:
    service, _, repository, _, _ = build_service()
    repository.get_by_id.return_value = None

    with pytest.raises(NotificationNotFoundError):
        await service.get_notification_by_id("missing")


@pytest.mark.asyncio
async def test_get_notification_returns_cached_value() -> None:
    service, _, repository, _, cache = build_service()
    cache.get.return_value = NotificationRead.model_validate(
        notification()
    ).model_dump_json()

    result = await service.get_notification_by_id("notification-id")

    assert result.id == "notification-id"
    repository.get_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_invalidates_notification_caches() -> None:
    service, _, repository, _, cache = build_service()
    repository.get_by_id.return_value = notification()

    await service.update_notification(
        "notification-id",
        status=NotificationStatusEnum.SENT,
    )

    cache.delete.assert_awaited_once_with("notification-id", "user:user-id")
