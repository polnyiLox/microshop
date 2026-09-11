from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_order_service
from app.core.config import (
    CatalogCommandsExchangeSettings,
    OrderEventsExchangeSettings,
    PaymentCommandsExchangeSettings,
)
from app.main import app
from app.repositories import OrderItemRepository, OrderRepository
from app.services import OrderService


@pytest.mark.asyncio(loop_scope="session")
async def test_create_list_and_cancel_order(session: AsyncSession) -> None:
    catalog = AsyncMock()
    catalog.get_product.return_value = {
        "id": "product-id",
        "name": "E2E product",
        "price": 300,
        "quantity": 5,
        "seller_id": "seller-id",
    }
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_user_orders_key = Mock(side_effect=lambda user_id: f"user:{user_id}")
    cache.create_seller_orders_key = Mock(side_effect=lambda seller_id: f"seller:{seller_id}")
    cache.create_order_items_key = Mock(
        side_effect=lambda order_id, item_id="": f"{order_id}:items:{item_id}"
    )
    service = OrderService(
        OrderRepository(session),
        OrderItemRepository(session),
        session,
        catalog,
        AsyncMock(),
        OrderEventsExchangeSettings(),
        CatalogCommandsExchangeSettings(),
        PaymentCommandsExchangeSettings(),
        AsyncMock(),
        cache,
        SimpleNamespace(redis=SimpleNamespace(ttl_seconds=60)),
    )
    app.dependency_overrides[get_order_service] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/v1/orders",
                headers={"X-User-ID": "user-id"},
                json={"items": [{"product_id": "product-id", "quantity": 2}]},
            )
            order_id = created.json()["id"]
            listed = await client.get(
                "/v1/orders",
                headers={"X-User-ID": "user-id"},
            )
            cancelled = await client.post(
                f"/v1/orders/{order_id}/cancel",
                headers={"X-User-ID": "user-id"},
            )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["user_id"] == "user-id"
    assert created.json()["total_amount"] == 600
    assert [order["id"] for order in listed.json()] == [order_id]
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    catalog.release_product.assert_awaited_once_with(
        product_id="product-id", quantity=2
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_order_api_hides_another_users_order(
    session: AsyncSession,
) -> None:
    catalog = AsyncMock()
    catalog.get_product.return_value = {
        "id": "private-product",
        "name": "Private product",
        "price": 200,
        "quantity": 5,
        "seller_id": "seller-id",
    }
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_user_orders_key = Mock(
        side_effect=lambda user_id: f"user:{user_id}",
    )
    cache.create_seller_orders_key = Mock(
        side_effect=lambda seller_id: f"seller:{seller_id}",
    )
    cache.create_order_items_key = Mock(
        side_effect=lambda order_id, item_id="": f"{order_id}:items:{item_id}",
    )
    service = OrderService(
        OrderRepository(session),
        OrderItemRepository(session),
        session,
        catalog,
        AsyncMock(),
        OrderEventsExchangeSettings(),
        CatalogCommandsExchangeSettings(),
        PaymentCommandsExchangeSettings(),
        AsyncMock(),
        cache,
        SimpleNamespace(redis=SimpleNamespace(ttl_seconds=60)),
    )
    app.dependency_overrides[get_order_service] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/v1/orders",
                headers={"X-User-ID": "owner-id"},
                json={"items": [{"product_id": "private-product", "quantity": 1}]},
            )
            order_id = created.json()["id"]
            forbidden = await client.get(
                f"/v1/orders/{order_id}",
                headers={"X-User-ID": "another-user"},
            )
            another_users_orders = await client.get(
                "/v1/orders",
                headers={"X-User-ID": "another-user"},
            )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert forbidden.status_code == 404
    assert another_users_orders.status_code == 200
    assert another_users_orders.json() == []
