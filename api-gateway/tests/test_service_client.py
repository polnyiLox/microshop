from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from starlette.datastructures import Headers

from app.clients import ServiceClient
from app.exceptions import ServiceTimeoutError, ServiceUnavailableError


def build_request() -> Mock:
    request = Mock()
    request.method = "POST"
    request.url.path = "/v1/orders"
    request.url.query = "status=new"
    request.headers = Headers(
        {
            "authorization": "Bearer access-token",
            "content-type": "application/json",
            "cookie": "refresh_token=token",
            "host": "gateway:8080",
            "x-user-id": "spoofed-user",
            "x-user-role": "admin",
        }
    )
    request.body = AsyncMock(return_value=b'{"product_id":"product-id"}')
    return request


@pytest.mark.asyncio
async def test_forward_preserves_request_and_response() -> None:
    request = build_request()
    service_response = httpx.Response(
        status_code=201,
        content=b'{"id":"order-id"}',
        headers=[
            ("content-type", "application/json"),
            ("set-cookie", "refresh_token=new-token; HttpOnly"),
        ],
    )
    http_client = AsyncMock()
    http_client.request.return_value = service_response
    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = http_client

    with patch("app.clients.service.httpx.AsyncClient", return_value=context_manager):
        response = await ServiceClient(timeout_seconds=5).forward(
            request=request,
            service_url="http://order-service:8000/",
            user_id="user-id",
            user_role="user",
        )

    call = http_client.request.await_args.kwargs

    assert call["method"] == "POST"
    assert call["url"] == "http://order-service:8000/v1/orders?status=new"
    assert call["content"] == b'{"product_id":"product-id"}'
    assert call["headers"]["authorization"] == "Bearer access-token"
    assert call["headers"]["cookie"] == "refresh_token=token"
    assert "host" not in call["headers"]
    assert call["headers"]["x-user-id"] == "user-id"
    assert call["headers"]["x-user-role"] == "user"
    assert response.status_code == 201
    assert response.body == b'{"id":"order-id"}'
    assert response.headers["set-cookie"] == "refresh_token=new-token; HttpOnly"


@pytest.mark.asyncio
async def test_forward_reports_timeout() -> None:
    request = build_request()
    http_client = AsyncMock()
    http_client.request.side_effect = httpx.ReadTimeout("timeout")
    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = http_client

    with patch("app.clients.service.httpx.AsyncClient", return_value=context_manager):
        with pytest.raises(ServiceTimeoutError):
            await ServiceClient(timeout_seconds=5).forward(
                request=request,
                service_url="http://order-service:8000",
            )


@pytest.mark.asyncio
async def test_forward_reports_unavailable_service() -> None:
    request = build_request()
    http_client = AsyncMock()
    http_client.request.side_effect = httpx.ConnectError("unavailable")
    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = http_client

    with patch("app.clients.service.httpx.AsyncClient", return_value=context_manager):
        with pytest.raises(ServiceUnavailableError):
            await ServiceClient(timeout_seconds=5).forward(
                request=request,
                service_url="http://order-service:8000",
            )
