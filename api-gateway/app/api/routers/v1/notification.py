from fastapi import APIRouter, Depends, Request, Response, WebSocket

from app.api.dependencies import get_current_user, get_service_client
from app.clients import ServiceClient
from app.core.config import settings
from app.exceptions import InvalidAccessTokenError
from app.schemas import CurrentUser
from app.security import get_user_from_access_token
from app.websocket import proxy_notification_websocket


router = APIRouter(prefix="/notifications", tags=["Уведомления"])


def get_websocket_access_token(subprotocols: list[str]) -> str | None:
    """Read a bearer token without putting credentials in the WebSocket URL."""
    if len(subprotocols) != 2 or subprotocols[0].lower() != "bearer":
        return None
    return subprotocols[1]


@router.api_route("", methods=["GET"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET"], include_in_schema=False)
async def proxy_notifications(
    request: Request,
    path: str = "",
    current_user: CurrentUser = Depends(get_current_user),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await client.forward(
        request,
        settings.services.notification_url,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.websocket("/ws")
async def notifications_websocket(
    websocket: WebSocket,
) -> None:
    subprotocols = websocket.scope.get("subprotocols", [])
    access_token = get_websocket_access_token(subprotocols)
    if access_token is None:
        await websocket.close(code=1008)
        return

    try:
        current_user = get_user_from_access_token(access_token)
    except InvalidAccessTokenError:
        await websocket.close(code=1008)
        return

    await proxy_notification_websocket(
        client_websocket=websocket,
        service_url=settings.services.notification_url,
        user_id=current_user.id,
        client_subprotocol="bearer",
    )
