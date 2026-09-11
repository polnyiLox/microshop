from unittest.mock import patch

import httpx
import pytest

from app.api.dependencies import get_current_user
from app.main import app
from app.schemas import CurrentUser


@pytest.mark.asyncio
async def test_authenticated_order_request_crosses_gateway_stack() -> None:
    forwarded_requests: list[httpx.Request] = []

    def downstream(request: httpx.Request) -> httpx.Response:
        forwarded_requests.append(request)
        return httpx.Response(
            200,
            json={"orders": [{"id": "order-id"}]},
            headers={"X-Service": "order"},
        )

    downstream_client = httpx.AsyncClient(
        transport=httpx.MockTransport(downstream)
    )
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="user-id",
        role="user",
    )
    gateway_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://gateway",
    )

    try:
        with patch(
            "app.clients.service.httpx.AsyncClient",
            return_value=downstream_client,
        ):
            response = await gateway_client.get(
                "/v1/orders?status=created",
                headers={"Authorization": "Bearer token"},
            )
    finally:
        await gateway_client.aclose()
        if not downstream_client.is_closed:
            await downstream_client.aclose()
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"orders": [{"id": "order-id"}]}
    assert response.headers["X-Service"] == "order"
    assert len(forwarded_requests) == 1
    forwarded = forwarded_requests[0]
    assert forwarded.url.path == "/v1/orders"
    assert forwarded.url.query == b"status=created"
    assert forwarded.headers["X-User-ID"] == "user-id"
    assert forwarded.headers["X-User-Role"] == "user"
