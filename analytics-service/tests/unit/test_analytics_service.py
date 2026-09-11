from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.enums import RevenueGroupByEnum
from app.services import AnalyticsService


def build_service(repository: AsyncMock) -> tuple[AnalyticsService, AsyncMock]:
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_overview_key = Mock(return_value="overview")
    return AnalyticsService(repository, cache, 60), cache


@pytest.mark.asyncio
async def test_overview_derives_net_and_average_revenue() -> None:
    repository = AsyncMock()
    repository.get_overview.return_value = {
        "orders_total": 4,
        "successful_payments": 2,
        "gross_revenue": 1000,
        "refunded_payments": 1,
        "refunded_amount": 250,
    }

    service, cache = build_service(repository)

    result = await service.get_overview()

    assert result.net_revenue == 750
    assert result.average_payment_amount == 500
    assert result.failed_payments == 0
    cache.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_payment_rates_handle_real_denominators() -> None:
    repository = AsyncMock()
    repository.get_payments.return_value = {
        "payments_total": 4,
        "successful_payments": 2,
        "refunded_payments": 1,
        "gross_revenue": 800,
        "refunded_amount": 200,
    }

    result = await build_service(repository)[0].get_payments()

    assert result.success_rate == 50
    assert result.refund_rate == 50
    assert result.average_payment_amount == 400


@pytest.mark.asyncio
async def test_revenue_rows_are_mapped_with_net_amount() -> None:
    repository = AsyncMock()
    period = datetime(2026, 8, 1, tzinfo=UTC)
    repository.get_revenue.return_value = [{
        "_id": period,
        "successful_payments": 3,
        "gross_revenue": 1200,
        "refunded_amount": 200,
    }]

    result = await build_service(repository)[0].get_revenue(RevenueGroupByEnum.DAY)

    assert result[0].period == period
    assert result[0].net_revenue == 1000


@pytest.mark.asyncio
async def test_overview_returns_cached_value() -> None:
    repository = AsyncMock()
    service, cache = build_service(repository)
    cache.get.return_value = '{"orders_total":2,"successful_payments":1,"failed_payments":0,"cancelled_payments":0,"refunded_payments":0,"gross_revenue":500,"refunded_amount":0,"net_revenue":500,"average_payment_amount":500.0}'

    result = await service.get_overview()

    assert result.orders_total == 2
    repository.get_overview.assert_not_awaited()
