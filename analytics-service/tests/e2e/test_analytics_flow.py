from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient
from pymongo.asynchronous.database import AsyncDatabase

from app.api.dependencies import get_analytics_service
from app.main import app
from app.repositories import AnalyticsEventRepository, AnalyticsRepository
from app.schemas import AnalyticsEventSchema
from app.services import AnalyticsService


@pytest.mark.asyncio(loop_scope="session")
async def test_overview_and_top_products_http_flow(
    database: AsyncDatabase,
    clean_database: None,
) -> None:
    events = AnalyticsEventRepository(database)
    occurred_at = datetime(2026, 8, 1, tzinfo=UTC)
    await events.create(AnalyticsEventSchema(
        event_id="e2e-order",
        event_type="order.created",
        event_version=1,
        occurred_at=occurred_at,
        producer="order-service",
        payload={
            "order_id": "order-id",
            "total_amount": 600,
            "status": "created",
            "items": [{
                "product_id": "product-id",
                "product_name": "E2E product",
                "quantity": 2,
                "unit_price": 300,
            }],
        },
    ))
    await events.create(AnalyticsEventSchema(
        event_id="e2e-payment",
        event_type="payment.succeeded",
        event_version=1,
        occurred_at=occurred_at,
        producer="payment-service",
        payload={"payment_id": "payment-id", "amount": 600},
    ))
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_overview_key = Mock(return_value="overview")
    service = AnalyticsService(AnalyticsRepository(database), cache, 60)
    app.dependency_overrides[get_analytics_service] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            overview = await client.get("/v1/analytics/overview")
            orders = await client.get("/v1/analytics/orders")
            payments = await client.get("/v1/analytics/payments")
            revenue = await client.get("/v1/analytics/revenue", params={"group_by": "day"})
            products = await client.get("/v1/analytics/products/top", params={"limit": 1})
    finally:
        app.dependency_overrides.clear()

    assert overview.status_code == 200
    assert overview.json()["orders_total"] == 1
    assert overview.json()["gross_revenue"] == 600
    assert orders.status_code == 200
    assert orders.json()["orders_total"] == 1
    assert orders.json()["orders_by_status"] == {"created": 1}
    assert payments.status_code == 200
    assert payments.json()["successful_payments"] == 1
    assert payments.json()["gross_revenue"] == 600
    assert revenue.status_code == 200
    assert revenue.json()[0]["gross_revenue"] == 600
    assert products.status_code == 200
    assert products.json()[0]["product_id"] == "product-id"
