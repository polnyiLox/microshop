import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect


logger = logging.getLogger(__name__)


class NotificationConnectionManager:
    """Track active WebSocket connections grouped by authenticated user."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()

        async with self._lock:
            self._connections.setdefault(user_id, set()).add(websocket)
            connection_count = len(self._connections[user_id])
        logger.info(
            "WebSocket connected user_id=%s active_connections=%s",
            user_id,
            connection_count,
        )

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            user_connections = self._connections.get(user_id)
            if user_connections is None:
                return

            user_connections.discard(websocket)
            if not user_connections:
                self._connections.pop(user_id, None)
            connection_count = len(user_connections)
        logger.info(
            "WebSocket disconnected user_id=%s active_connections=%s",
            user_id,
            connection_count,
        )

    async def send_to_user(self, user_id: str, notification: dict) -> None:
        async with self._lock:
            user_connections = list(self._connections.get(user_id, set()))
        logger.debug(
            "Sending notification over WebSocket user_id=%s connections=%s",
            user_id,
            len(user_connections),
        )

        disconnected_connections = []
        for websocket in user_connections:
            try:
                await websocket.send_json(notification)
            except (RuntimeError, WebSocketDisconnect):
                logger.debug("WebSocket send failed user_id=%s", user_id)
                disconnected_connections.append(websocket)

        for websocket in disconnected_connections:
            await self.disconnect(user_id, websocket)


notification_connection_manager = NotificationConnectionManager()
