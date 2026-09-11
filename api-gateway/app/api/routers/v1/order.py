from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import get_current_user, get_service_client, require_roles
from app.clients import ServiceClient
from app.core.config import settings
from app.enums import UserRole
from app.schemas import CurrentUser


router = APIRouter(prefix="/orders", tags=["Заказы"])


@router.get("/sales", include_in_schema=False)
async def proxy_seller_orders(
    request: Request,
    current_user: CurrentUser = Depends(require_roles(UserRole.SELLER)),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await client.forward(
        request,
        settings.services.order_url,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.api_route(
    "",
    methods=["GET", "POST", "PUT", "DELETE"],
    include_in_schema=False,
)
@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE"],
    include_in_schema=False,
)
async def proxy_orders(
    request: Request,
    path: str = "",
    current_user: CurrentUser = Depends(get_current_user),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await client.forward(
        request,
        settings.services.order_url,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.patch("/{order_id}/items/{order_item_id}", include_in_schema=False)
async def proxy_order_item_update(
    order_id: str,
    order_item_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await client.forward(
        request,
        settings.services.order_url,
        user_id=current_user.id,
        user_role=current_user.role,
    )
