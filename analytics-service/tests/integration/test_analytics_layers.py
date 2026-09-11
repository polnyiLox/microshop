from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.repositories import AnalyticsEventRepository, AnalyticsRepository
from app.schemas import AnalyticsEventSchema
from app.services import AnalyticsEventsService, AnalyticsService


pytestmark = pytest.mark.asyncio(loop_scope="session")


def event(event_id: str, event_type: str, payload: dict) -> AnalyticsEventSchema:
    return AnalyticsEventSchema(
        event_id=event_id,
        event_type=event_type,
        event_version=1,
        occurred_at=datetime(2026, 8, 1, tzinfo=UTC),
        producer="test",
        payload=payload,
    )


async def test_event_repository_enforces_idempotency(
    database: AsyncDatabase,
    clean_database: None,
) -> None:
    repository = AnalyticsEventRepository(database)
    cache = AsyncMock()
    cache.create_overview_key = Mock(return_value="overview")
    service = AnalyticsEventsService(repository, cache)
    created = event("same-event", "order.created", {"order_id": "order-id"})

    await service.process(created)
    await service.process(created)

    assert await database["analytics_events"].count_documents({}) == 1


async def test_service_aggregates_payments_and_products(
    database: AsyncDatabase,
    clean_database: None,
) -> None:
    events = AnalyticsEventRepository(database)
    for item in [
        event("order", "order.created", {
            "order_id": "order-id",
            "total_amount": 500,
            "status": "created",
            "items": [{
                "product_id": "product-id",
                "product_name": "Product",
                "quantity": 2,
                "unit_price": 250,
            }],
        }),
        event("payment-created", "payment.created", {
            "payment_id": "payment-id", "amount": 500
        }),
        event("payment-succeeded", "payment.succeeded", {
            "payment_id": "payment-id", "amount": 500
        }),
        event("payment-refunded", "payment.refunded", {
            "payment_id": "payment-id", "amount": 100
        }),
    ]:
        await events.create(item)

    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_overview_key = Mock(return_value="overview")
    service = AnalyticsService(AnalyticsRepository(database), cache, 60)
    overview = await service.get_overview()
    products = await service.get_top_products(limit=5)

    assert overview.orders_total == 1
    assert overview.net_revenue == 400
    assert products[0].product_id == "product-id"
    assert products[0].revenue == 500


async def test_service_applies_date_range_without_using_overview_cache(
    database: AsyncDatabase,
    clean_database: None,
) -> None:
    events = AnalyticsEventRepository(database)
    for event_id, occurred_at, amount in [
        ("before-range", datetime(2026, 7, 31, tzinfo=UTC), 100),
        ("inside-range", datetime(2026, 8, 15, tzinfo=UTC), 250),
        ("after-range", datetime(2026, 9, 1, tzinfo=UTC), 500),
    ]:
        await events.create(AnalyticsEventSchema(
            event_id=event_id,
            event_type="payment.succeeded",
            event_version=1,
            occurred_at=occurred_at,
            producer="payment-service",
            payload={"payment_id": event_id, "amount": amount},
        ))

    cache = AsyncMock()
    cache.create_overview_key = Mock(return_value="overview")
    service = AnalyticsService(AnalyticsRepository(database), cache, 60)
    overview = await service.get_overview(
        date_from=datetime(2026, 8, 1, tzinfo=UTC),
        date_to=datetime(2026, 8, 31, 23, 59, tzinfo=UTC),
    )

    assert overview.successful_payments == 1
    assert overview.gross_revenue == 250
    cache.get.assert_not_awaited()
    cache.set.assert_not_awaited()
