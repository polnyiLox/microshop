from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import get_service_client
from app.clients import ServiceClient
from app.core.config import settings


router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.api_route(
    "",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def proxy_auth(
    request: Request,
    path: str = "",
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await client.forward(request, settings.services.auth_url)

