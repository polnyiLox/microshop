from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket import notification_connection_manager


router = APIRouter(
    prefix="/notifications",
    tags=["Уведомления"],
)


@router.websocket("/ws/{user_id}")
async def notifications_websocket(
        websocket: WebSocket,
        user_id: str,
) -> None:
    if websocket.headers.get("X-User-ID") != user_id:
        await websocket.close(code=1008)
        return

    await notification_connection_manager.connect(user_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await notification_connection_manager.disconnect(user_id, websocket)
