import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.config import (
    CatalogCommandsExchangeSettings,
    OrderEventsExchangeSettings,
    PaymentCommandsExchangeSettings,
)
from app.enums import OrderStatusEnum
from app.exceptions import NotEnoughProductError, OrderItemAlreadyExistsError, OwnProductOrderError
from app.schemas import OrderItemCreate, OrderUpdateAllItems
from app.services import OrderService


def build_service():
    order_repo = AsyncMock()
    item_repo = AsyncMock()
    session = AsyncMock()
    catalog = AsyncMock()
    publisher = AsyncMock()
    kafka = AsyncMock()
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_user_orders_key = Mock(side_effect=lambda user_id: f"user:{user_id}")
    cache.create_seller_orders_key = Mock(side_effect=lambda seller_id: f"seller:{seller_id}")
    cache.create_order_items_key = Mock(
        side_effect=lambda order_id, item_id="": f"{order_id}:items:{item_id}"
    )
    settings = SimpleNamespace(redis=SimpleNamespace(ttl_seconds=60))
    service = OrderService(
        order_repo,
        item_repo,
        session,
        catalog,
        publisher,
        OrderEventsExchangeSettings(),
        CatalogCommandsExchangeSettings(),
        PaymentCommandsExchangeSettings(),
        kafka,
        cache,
        settings,
    )
    return service, order_repo, session, catalog, publisher, kafka, cache


@pytest.mark.asyncio
async def test_check_products_rejects_duplicate_without_second_call() -> None:
    service, _, _, catalog, _, _, _ = build_service()
    catalog.get_product.return_value = {
        "id": "product-id", "name": "Product", "price": 100, "quantity": 5,
        "seller_id": "seller-id",
    }

    with pytest.raises(OrderItemAlreadyExistsError):
        await service._check_products([
            OrderItemCreate(product_id="product-id", quantity=1),
            OrderItemCreate(product_id="product-id", quantity=2),
        ], user_id="buyer-id")

    catalog.get_product.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_products_calculates_total_and_rejects_shortage() -> None:
    service, _, _, catalog, _, _, _ = build_service()
    catalog.get_product.side_effect = [
        {"id": "first", "name": "First", "price": 100, "quantity": 5, "seller_id": "seller-id"},
        {"id": "second", "name": "Second", "price": 250, "quantity": 1, "seller_id": "seller-id"},
    ]

    with pytest.raises(NotEnoughProductError):
        await service._check_products([
            OrderItemCreate(product_id="first", quantity=2),
            OrderItemCreate(product_id="second", quantity=2),
        ], user_id="buyer-id")


@pytest.mark.asyncio
async def test_check_products_rejects_product_owned_by_buyer() -> None:
    service, _, _, catalog, _, _, _ = build_service()
    catalog.get_product.return_value = {
        "id": "product-id",
        "name": "Product",
        "price": 100,
        "quantity": 5,
        "seller_id": "seller-id",
    }

    with pytest.raises(OwnProductOrderError):
        await service._check_products(
            [OrderItemCreate(product_id="product-id", quantity=1)],
            user_id="seller-id",
        )


@pytest.mark.asyncio
async def test_inventory_reserved_advances_order_and_starts_payment() -> None:
    service, order_repo, session, _, publisher, _, cache = build_service()
    order = SimpleNamespace(
        id="order-id",
        user_id="user-id",
        total_amount=0,
        status=OrderStatusEnum.CREATED,
        items=[],
    )
    order_repo.get_by_id.return_value = order
    service._publish_analytics_event = AsyncMock()

    await service.handle_inventory_reserved({
        "order_id": "order-id",
        "total_amount": 900,
    })

    assert order.status == OrderStatusEnum.WAITING_PAYMENT
    assert order.total_amount == 900
    session.commit.assert_awaited_once()
    assert publisher.publish.await_count == 2
    service._publish_analytics_event.assert_awaited_once()
    invalidated_keys = {
        key
        for call in cache.delete.await_args_list
        for key in call.args
    }
    assert {"order-id", "user:user-id"} <= invalidated_keys


@pytest.mark.asyncio
async def test_cancelling_paid_order_requests_refund_without_mutating_status() -> None:
    service, order_repo, session, _, publisher, _, _ = build_service()
    order = SimpleNamespace(
        id="order-id",
        user_id="user-id",
        total_amount=500,
        status=OrderStatusEnum.PAID,
        created_at=datetime.now(UTC),
        items=[],
    )
    order_repo.get_by_id.return_value = order

    result = await service.cancel_order("order-id")

    assert result.status == OrderStatusEnum.PAID
    publisher.publish.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_order_returns_cached_value() -> None:
    service, order_repo, _, _, _, _, cache = build_service()
    cache.get.return_value = json.dumps({
        "id": "order-id",
        "user_id": "user-id",
        "status": "created",
        "total_amount": 500,
        "created_at": datetime.now(UTC).isoformat(),
        "items": [],
    })

    result = await service.get_order_by_id("order-id")

    assert result.id == "order-id"
    order_repo.get_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_replace_items_moves_inventory_to_new_products() -> None:
    service, order_repo, session, catalog, _, _, _ = build_service()
    order_repo.get_by_id.return_value = SimpleNamespace(
        id="order-id",
        user_id="buyer-id",
        total_amount=100,
        status=OrderStatusEnum.CREATED,
        created_at=datetime.now(UTC),
        items=[SimpleNamespace(
            id="old-item-id",
            order_id="order-id",
            product_id="old-product",
            seller_id="old-seller",
            product_name="Old product",
            quantity=1,
            unit_price=100,
        )],
    )
    catalog.get_product.return_value = {
        "id": "new-product",
        "name": "New product",
        "price": 300,
        "quantity": 5,
        "seller_id": "new-seller",
    }

    result = await service.update_all_items(
        "order-id",
        OrderUpdateAllItems(items=[
            OrderItemCreate(product_id="new-product", quantity=2),
        ]),
    )

    assert result.total_amount == 600
    catalog.release_product.assert_awaited_once_with(
        product_id="old-product",
        quantity=1,
    )
    catalog.reserve_product.assert_awaited_once_with(
        product_id="new-product",
        quantity=2,
    )
    service._order_item_repo.delete_all_by_order_id.assert_awaited_once_with("order-id")
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_replace_items_restores_old_inventory_after_validation_error() -> None:
    service, order_repo, session, catalog, _, _, _ = build_service()
    order_repo.get_by_id.return_value = SimpleNamespace(
        id="order-id",
        user_id="buyer-id",
        total_amount=100,
        status=OrderStatusEnum.CREATED,
        created_at=datetime.now(UTC),
        items=[SimpleNamespace(
            id="old-item-id",
            order_id="order-id",
            product_id="old-product",
            seller_id="old-seller",
            product_name="Old product",
            quantity=1,
            unit_price=100,
        )],
    )
    catalog.get_product.return_value = {
        "id": "new-product",
        "name": "New product",
        "price": 300,
        "quantity": 0,
        "seller_id": "new-seller",
    }

    with pytest.raises(NotEnoughProductError):
        await service.update_all_items(
            "order-id",
            OrderUpdateAllItems(items=[
                OrderItemCreate(product_id="new-product", quantity=2),
            ]),
        )

    catalog.release_product.assert_awaited_once_with(
        product_id="old-product",
        quantity=1,
    )
    catalog.reserve_product.assert_awaited_once_with(
        product_id="old-product",
        quantity=1,
    )
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
