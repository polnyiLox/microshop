from unittest.mock import AsyncMock

import pytest

from app.websocket import NotificationConnectionManager


@pytest.mark.asyncio
async def test_send_to_user_removes_failed_connections() -> None:
    manager = NotificationConnectionManager()
    connected = AsyncMock()
    disconnected = AsyncMock()
    disconnected.send_json.side_effect = RuntimeError("closed")
    await manager.connect("user-id", connected)
    await manager.connect("user-id", disconnected)

    await manager.send_to_user("user-id", {"id": "notification-id"})

    connected.send_json.assert_awaited_once_with({"id": "notification-id"})
    assert connected in manager._connections["user-id"]
    assert disconnected not in manager._connections["user-id"]
