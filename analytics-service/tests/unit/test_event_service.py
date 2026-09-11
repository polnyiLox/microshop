from unittest.mock import AsyncMock, Mock

import pytest
from pymongo.errors import DuplicateKeyError

from app.schemas import AnalyticsEventSchema
from app.services import AnalyticsEventsService


@pytest.mark.asyncio
async def test_duplicate_event_is_idempotently_ignored() -> None:
    repository = AsyncMock()
    cache = AsyncMock()
    cache.create_overview_key = Mock(return_value="overview")
    repository.create.side_effect = DuplicateKeyError("duplicate")
    event = AnalyticsEventSchema(
        event_id="event-id",
        event_type="order.created",
        event_version=1,
        occurred_at="2026-08-01T00:00:00Z",
        producer="order-service",
        payload={"order_id": "order-id"},
    )

    await AnalyticsEventsService(repository, cache).process(event)

    repository.create.assert_awaited_once_with(event)
    cache.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_created_event_invalidates_overview() -> None:
    repository = AsyncMock()
    cache = AsyncMock()
    cache.create_overview_key = Mock(return_value="overview")
    event = AnalyticsEventSchema(
        event_id="event-id",
        event_type="order.created",
        event_version=1,
        occurred_at="2026-08-01T00:00:00Z",
        producer="order-service",
        payload={"order_id": "order-id"},
    )

    await AnalyticsEventsService(repository, cache).process(event)

    cache.delete.assert_awaited_once_with("overview")
