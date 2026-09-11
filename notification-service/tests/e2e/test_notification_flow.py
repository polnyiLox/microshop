from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_notification_service
from app.main import app
from app.repositories import NotificationRepository
from app.services import NotificationService


@pytest.mark.asyncio(loop_scope="session")
async def test_user_reads_only_own_notifications(session: AsyncSession) -> None:
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_user_notifications_key = Mock(
        side_effect=lambda user_id: f"user:{user_id}"
    )
    service = NotificationService(
        session,
        NotificationRepository(session),
        AsyncMock(),
        cache,
        SimpleNamespace(redis=SimpleNamespace(ttl_seconds=60)),
    )
    own = await service.create_notification("user-id", {"text": "hello"})
    private = await service.create_notification(
        "other-user",
        {"text": "private"},
    )
    app.dependency_overrides[get_notification_service] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            listed = await client.get(
                "/v1/notifications/users/user-id",
                headers={"X-User-ID": "user-id"},
            )
            fetched = await client.get(
                f"/v1/notifications/{own.id}",
                headers={"X-User-ID": "user-id"},
            )
            forbidden = await client.get(
                "/v1/notifications/users/other-user",
                headers={"X-User-ID": "user-id"},
            )
            private_notification = await client.get(
                f"/v1/notifications/{private.id}",
                headers={"X-User-ID": "user-id"},
            )
    finally:
        app.dependency_overrides.clear()

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [own.id]
    assert fetched.status_code == 200
    assert forbidden.status_code == 404
    assert private_notification.status_code == 404
