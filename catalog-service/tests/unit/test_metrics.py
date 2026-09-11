from types import SimpleNamespace

import pytest
from fastapi import Request, Response

from app.core.metrics import HTTP_REQUESTS, prometheus_metrics, record_http_metrics


@pytest.mark.asyncio
async def test_request_metrics_use_route_template() -> None:
    labels = {
        "method": "GET",
        "path": "/v1/products/{product_id}",
        "status": "200",
    }
    counter = HTTP_REQUESTS.labels(**labels)
    previous_value = counter._value.get()
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/v1/products/product-id",
        "headers": [],
        "query_string": b"",
        "route": SimpleNamespace(path=labels["path"]),
    })

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = await record_http_metrics(request, call_next)

    assert response.status_code == 200
    assert counter._value.get() == previous_value + 1


@pytest.mark.asyncio
async def test_metrics_endpoint_uses_prometheus_format() -> None:
    response = await prometheus_metrics()

    assert response.headers["content-type"].startswith("text/plain")
    assert b"catalog_http_requests_total" in response.body
