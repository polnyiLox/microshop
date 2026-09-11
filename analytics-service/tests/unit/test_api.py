from unittest.mock import AsyncMock

import pytest

from app.api.routers.v1.analytics import get_analytics_overview, get_top_products


@pytest.mark.asyncio
async def test_overview_endpoint_forwards_date_range() -> None:
    service = AsyncMock()

    await get_analytics_overview(None, None, service)

    service.get_overview.assert_awaited_once_with(date_from=None, date_to=None)


@pytest.mark.asyncio
async def test_top_products_endpoint_forwards_limit() -> None:
    service = AsyncMock()

    await get_top_products(5, None, None, service)

    service.get_top_products.assert_awaited_once_with(
        limit=5, date_from=None, date_to=None
    )
