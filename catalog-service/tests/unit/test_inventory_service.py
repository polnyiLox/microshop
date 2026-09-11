from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.config import CatalogEventsExchangeSettings
from app.exceptions import NotEnoughProductError
from app.services import InventoryService


@pytest.mark.asyncio
async def test_reserve_publishes_priced_items_and_total() -> None:
    product_service = AsyncMock()
    product_service.reserve_products.return_value = [
        SimpleNamespace(id="first", price=100),
        SimpleNamespace(id="second", price=250),
    ]
    publisher = AsyncMock()
    settings = CatalogEventsExchangeSettings()
    service = InventoryService(product_service, publisher, settings)

    await service.reserve({
        "order_id": "order-id",
        "items": [
            {"product_id": "first", "quantity": 2},
            {"product_id": "second", "quantity": 1},
        ],
    })

    publisher.publish.assert_awaited_once_with(
        settings.reserved_routing_key,
        {
            "order_id": "order-id",
            "items": [
                {"product_id": "first", "quantity": 2, "unit_price": 100},
                {"product_id": "second", "quantity": 1, "unit_price": 250},
            ],
            "total_amount": 450,
        },
    )


@pytest.mark.asyncio
async def test_reservation_failure_is_converted_to_event() -> None:
    product_service = AsyncMock()
    product_service.reserve_products.side_effect = NotEnoughProductError()
    publisher = AsyncMock()
    settings = CatalogEventsExchangeSettings()

    await InventoryService(product_service, publisher, settings).reserve({
        "order_id": "order-id",
        "items": [{"product_id": "product-id", "quantity": 99}],
    })

    publisher.publish.assert_awaited_once_with(
        settings.reservation_failed_routing_key,
        {"order_id": "order-id", "reason": NotEnoughProductError.detail},
    )
