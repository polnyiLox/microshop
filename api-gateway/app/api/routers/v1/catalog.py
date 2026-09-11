from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import get_service_client, require_roles
from app.clients import ServiceClient
from app.core.config import settings
from app.enums import UserRole
from app.schemas import CurrentUser


router = APIRouter(prefix="/products", tags=["Каталог"])


@router.api_route("", methods=["GET"], include_in_schema=False)
@router.api_route("/{path:path}", methods=["GET"], include_in_schema=False)
async def proxy_catalog_read(
    request: Request,
    path: str = "",
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await client.forward(request, settings.services.catalog_url)


async def _forward_catalog_write(
    request: Request,
    current_user: CurrentUser,
    client: ServiceClient,
) -> Response:
    return await client.forward(
        request,
        settings.services.catalog_url,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.post("", include_in_schema=False)
async def proxy_product_creation(
    request: Request,
    current_user: CurrentUser = Depends(require_roles(UserRole.SELLER)),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await _forward_catalog_write(request, current_user, client)


@router.patch("/{product_id}", include_in_schema=False)
async def proxy_product_update(
    product_id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_roles(UserRole.SELLER)),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await _forward_catalog_write(request, current_user, client)


@router.put("/{product_id}/image", include_in_schema=False)
async def proxy_product_image_upload(
    product_id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_roles(UserRole.SELLER)),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await _forward_catalog_write(request, current_user, client)


@router.delete("/{product_id}", include_in_schema=False)
async def proxy_product_deletion(
    product_id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_roles(UserRole.SELLER)),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await _forward_catalog_write(request, current_user, client)
