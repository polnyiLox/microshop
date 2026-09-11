from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_analytics_service
from app.enums import RevenueGroupByEnum
from app.schemas import (
    AnalyticsOverview,
    OrderAnalytics,
    PaymentAnalytics,
    RevenuePoint,
    TopProduct,
)
from app.services import AnalyticsService


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsOverview:
    return await service.get_overview(
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/orders", response_model=OrderAnalytics)
async def get_order_analytics(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
) -> OrderAnalytics:
    return await service.get_orders(
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/payments", response_model=PaymentAnalytics)
async def get_payment_analytics(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
) -> PaymentAnalytics:
    return await service.get_payments(
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/revenue", response_model=list[RevenuePoint])
async def get_revenue_analytics(
    group_by: RevenueGroupByEnum = RevenueGroupByEnum.DAY,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[RevenuePoint]:
    return await service.get_revenue(
        group_by=group_by,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/products/top", response_model=list[TopProduct])
async def get_top_products(
    limit: int = Query(default=10, ge=1, le=100),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[TopProduct]:
    return await service.get_top_products(
        limit=limit,
        date_from=date_from,
        date_to=date_to,
    )
