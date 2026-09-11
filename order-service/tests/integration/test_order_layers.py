from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    CatalogCommandsExchangeSettings,
    OrderEventsExchangeSettings,
    PaymentCommandsExchangeSettings,
)
from app.repositories import OrderItemRepository, OrderRepository
from app.schemas import OrderCreate, OrderItemCreate, OrderItemUpdate
from app.services import OrderService


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_repositories_persist_items_and_calculate_total(session: AsyncSession) -> None:
    orders = OrderRepository(session)
    items = OrderItemRepository(session)
    order = await orders.create("user-id", 0)
    await items.create(order.id, "first", "seller-id", "First", 2, 100)
    await items.create(order.id, "second", "seller-id", "Second", 1, 250)

    assert await orders.calculate_total_amount(order.id) == 450
    loaded = await orders.get_by_id(order.id)
    assert loaded is not None
    assert len(loaded.items) == 2


async def test_service_creates_order_with_real_repositories(session: AsyncSession) -> None:
    catalog = AsyncMock()
    catalog.get_product.side_effect = [
        {"id": "first", "name": "First product", "price": 100, "quantity": 10, "seller_id": "seller-id"},
        {"id": "second", "name": "Second product", "price": 250, "quantity": 10, "seller_id": "seller-id"},
    ]
    publisher = AsyncMock()
    kafka = AsyncMock()
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
        publisher,
        OrderEventsExchangeSettings(),
        CatalogCommandsExchangeSettings(),
        PaymentCommandsExchangeSettings(),
        kafka,
        cache,
        SimpleNamespace(redis=SimpleNamespace(ttl_seconds=60)),
    )

    created = await service.create_order(OrderCreate(
        user_id="service-user",
        items=[
            OrderItemCreate(product_id="first", quantity=2),
            OrderItemCreate(product_id="second", quantity=1),
        ],
    ))

    assert created.total_amount == 450
    assert len(created.items) == 2
    publisher.publish.assert_awaited_once()
    kafka.publish.assert_awaited_once()


async def test_service_updates_item_and_persists_recalculated_total(
    session: AsyncSession,
) -> None:
    catalog = AsyncMock()
    catalog.get_product.return_value = {
        "id": "updated-product",
        "name": "Updated product",
        "price": 125,
        "quantity": 10,
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
    orders = OrderRepository(session)
    items = OrderItemRepository(session)
    service = OrderService(
        orders,
        items,
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
    order = await service.create_order(OrderCreate(
        user_id="item-user",
        items=[OrderItemCreate(product_id="updated-product", quantity=2)],
    ))

    updated_item = await service.update_item_in_order(
        order.id,
        order.items[0].id,
        OrderItemUpdate(quantity=4),
    )
    stored_order = await orders.get_by_id(order.id)

    assert updated_item.quantity == 4
    assert stored_order is not None
    assert stored_order.total_amount == 500
    assert stored_order.items[0].quantity == 4
    catalog.reserve_product.assert_awaited_once_with(
        product_id="updated-product",
        quantity=2,
    )
