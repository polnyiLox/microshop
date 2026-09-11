from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import get_service_client, require_roles
from app.clients import ServiceClient
from app.core.config import settings
from app.enums import UserRole
from app.schemas import CurrentUser


router = APIRouter(prefix="/analytics", tags=["Аналитика"])


@router.api_route("", methods=["GET"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET"], include_in_schema=False)
async def proxy_analytics(
    request: Request,
    path: str = "",
    current_user: CurrentUser = Depends(require_roles(UserRole.ADMIN)),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await client.forward(
        request,
        settings.services.analytics_url,
        user_id=current_user.id,
        user_role=current_user.role,
    )
