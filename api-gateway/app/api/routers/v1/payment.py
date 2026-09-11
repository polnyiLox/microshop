from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import get_current_user, get_service_client
from app.clients import ServiceClient
from app.core.config import settings
from app.schemas import CurrentUser


router = APIRouter(prefix="/payments", tags=["Платежи"])


async def _forward_payment_request(
    request: Request,
    current_user: CurrentUser,
    client: ServiceClient,
) -> Response:
    return await client.forward(
        request,
        settings.services.payment_url,
        user_id=current_user.id,
        user_role=current_user.role,
    )


@router.get("", include_in_schema=False)
async def proxy_payment_list(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await _forward_payment_request(request, current_user, client)


@router.get("/{payment_id}", include_in_schema=False)
async def proxy_payment_detail(
    payment_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await _forward_payment_request(request, current_user, client)


@router.post("/{payment_id}/complete", include_in_schema=False)
async def proxy_payment_completion(
    payment_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await _forward_payment_request(request, current_user, client)


@router.post("/{payment_id}/cancel", include_in_schema=False)
async def proxy_payment_cancellation(
    payment_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await _forward_payment_request(request, current_user, client)


@router.post("/{payment_id}/retry", include_in_schema=False)
async def proxy_payment_retry(
    payment_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    client: ServiceClient = Depends(get_service_client),
) -> Response:
    return await _forward_payment_request(request, current_user, client)
