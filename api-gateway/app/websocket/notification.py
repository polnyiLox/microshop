import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed


logger = logging.getLogger(__name__)


async def proxy_notification_websocket(
    client_websocket: WebSocket,
    service_url: str,
    user_id: str,
    client_subprotocol: str,
) -> None:
    target_url = build_notification_websocket_url(service_url, user_id)
    logger.info("Opening notification WebSocket proxy: user_id=%s", user_id)

    try:
        async with connect(
            target_url,
            additional_headers={"X-User-ID": user_id},
        ) as service_websocket:
            await client_websocket.accept(subprotocol=client_subprotocol)
            logger.info("Notification WebSocket proxy connected: user_id=%s", user_id)
            await _exchange_messages(client_websocket, service_websocket)
    except OSError as exc:
        logger.error(
            "Notification WebSocket upstream unavailable: user_id=%s, error=%s",
            user_id,
            exc,
        )
        await client_websocket.close(code=1011)
    finally:
        logger.info("Notification WebSocket proxy closed: user_id=%s", user_id)


def build_notification_websocket_url(service_url: str, user_id: str) -> str:
    websocket_url = service_url.rstrip("/")
    websocket_url = websocket_url.replace("https://", "wss://", 1)
    websocket_url = websocket_url.replace("http://", "ws://", 1)
    return f"{websocket_url}/v1/notifications/ws/{user_id}"


async def _exchange_messages(
    client_websocket: WebSocket,
    service_websocket: ClientConnection,
) -> None:
    client_task = asyncio.create_task(
        _forward_client_messages(client_websocket, service_websocket)
    )
    service_task = asyncio.create_task(
        _forward_service_messages(client_websocket, service_websocket)
    )

    done_tasks, pending_tasks = await asyncio.wait(
        [client_task, service_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending_tasks:
        task.cancel()

    await asyncio.gather(*done_tasks, *pending_tasks, return_exceptions=True)


async def _forward_client_messages(
    client_websocket: WebSocket,
    service_websocket: ClientConnection,
) -> None:
    try:
        while True:
            message = await client_websocket.receive_text()
            await service_websocket.send(message)
    except WebSocketDisconnect:
        return


async def _forward_service_messages(
    client_websocket: WebSocket,
    service_websocket: ClientConnection,
) -> None:
    try:
        async for message in service_websocket:
            if isinstance(message, bytes):
                await client_websocket.send_bytes(message)
            else:
                await client_websocket.send_text(message)
    except ConnectionClosed:
        return
