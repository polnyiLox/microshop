import logging
from datetime import datetime

from pydantic import ValidationError

from app.cache import RedisCache
from app.enums import RevenueGroupByEnum
from app.repositories import AnalyticsRepository
from app.schemas import (
    AnalyticsOverview,
    OrderAnalytics,
    PaymentAnalytics,
    RevenuePoint,
    TopProduct,
)


logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(
        self,
        repository: AnalyticsRepository,
        redis_cache: RedisCache,
        cache_ttl_seconds: int,
    ) -> None:
        self._repository = repository
        self._redis_cache = redis_cache
        self._cache_ttl_seconds = cache_ttl_seconds

    async def get_overview(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> AnalyticsOverview:
        logger.debug(
            "Building analytics overview: date_from=%s, date_to=%s",
            date_from,
            date_to,
        )
        use_cache = date_from is None and date_to is None
        cache_key = self._redis_cache.create_overview_key()
        if use_cache:
            cached_overview = await self._redis_cache.get(cache_key)
            if cached_overview is not None:
                logger.debug("Analytics overview cache hit")
                try:
                    return AnalyticsOverview.model_validate_json(cached_overview)
                except ValidationError:
                    logger.warning("Invalid analytics overview found in cache")
                    await self._redis_cache.delete(cache_key)
            else:
                logger.debug("Analytics overview cache miss")

        logger.debug("Querying MongoDB for analytics overview")
        metrics = await self._repository.get_overview(
            date_from=date_from,
            date_to=date_to,
        )

        successful_payments = metrics.get("successful_payments", 0)
        gross_revenue = metrics.get("gross_revenue", 0)
        refunded_amount = metrics.get("refunded_amount", 0)

        average_payment_amount = 0.0
        if successful_payments:
            average_payment_amount = gross_revenue / successful_payments

        overview = AnalyticsOverview(
            orders_total=metrics.get("orders_total", 0),
            successful_payments=successful_payments,
            failed_payments=metrics.get("failed_payments", 0),
            cancelled_payments=metrics.get("cancelled_payments", 0),
            refunded_payments=metrics.get("refunded_payments", 0),
            gross_revenue=gross_revenue,
            refunded_amount=refunded_amount,
            net_revenue=gross_revenue - refunded_amount,
            average_payment_amount=average_payment_amount,
        )
        if use_cache:
            await self._redis_cache.set(
                cache_key,
                overview.model_dump_json(),
                self._cache_ttl_seconds,
            )
        logger.debug("Analytics overview built successfully")
        return overview

    async def get_orders(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> OrderAnalytics:
        logger.debug(
            "Building order analytics: date_from=%s, date_to=%s",
            date_from,
            date_to,
        )
        report = await self._repository.get_orders(
            date_from=date_from,
            date_to=date_to,
        )

        created = report.get("created", [])
        created_metrics = created[0] if created else {}
        orders_by_status = {
            row["_id"]: row["count"]
            for row in report.get("statuses", [])
            if row.get("_id") is not None
        }

        result = OrderAnalytics(
            orders_total=created_metrics.get("orders_total", 0),
            cancelled_orders=orders_by_status.get("cancelled", 0),
            failed_orders=orders_by_status.get("failed", 0),
            orders_by_status=orders_by_status,
            average_order_value=created_metrics.get("average_order_value", 0),
        )
        logger.debug("Order analytics built successfully")
        return result

    async def get_payments(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> PaymentAnalytics:
        logger.debug(
            "Building payment analytics: date_from=%s, date_to=%s",
            date_from,
            date_to,
        )
        metrics = await self._repository.get_payments(
            date_from=date_from,
            date_to=date_to,
        )

        payments_total = metrics.get("payments_total", 0)
        successful_payments = metrics.get("successful_payments", 0)
        refunded_payments = metrics.get("refunded_payments", 0)
        gross_revenue = metrics.get("gross_revenue", 0)

        success_rate = 0.0
        if payments_total:
            success_rate = successful_payments / payments_total * 100

        refund_rate = 0.0
        if successful_payments:
            refund_rate = refunded_payments / successful_payments * 100

        average_payment_amount = 0.0
        if successful_payments:
            average_payment_amount = gross_revenue / successful_payments

        result = PaymentAnalytics(
            payments_total=payments_total,
            successful_payments=successful_payments,
            failed_payments=metrics.get("failed_payments", 0),
            cancelled_payments=metrics.get("cancelled_payments", 0),
            refunded_payments=refunded_payments,
            gross_revenue=gross_revenue,
            refunded_amount=metrics.get("refunded_amount", 0),
            success_rate=success_rate,
            refund_rate=refund_rate,
            average_payment_amount=average_payment_amount,
        )
        logger.debug("Payment analytics built successfully")
        return result

    async def get_revenue(
        self,
        group_by: RevenueGroupByEnum,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[RevenuePoint]:
        logger.debug(
            "Building revenue analytics: group_by=%s, date_from=%s, date_to=%s",
            group_by,
            date_from,
            date_to,
        )
        rows = await self._repository.get_revenue(
            group_by=group_by,
            date_from=date_from,
            date_to=date_to,
        )

        result = [
            RevenuePoint(
                period=row["_id"],
                successful_payments=row.get("successful_payments", 0),
                gross_revenue=row.get("gross_revenue", 0),
                refunded_amount=row.get("refunded_amount", 0),
                net_revenue=(
                    row.get("gross_revenue", 0)
                    - row.get("refunded_amount", 0)
                ),
            )
            for row in rows
        ]
        logger.debug("Revenue analytics built: points=%d", len(result))
        return result

    async def get_top_products(
        self,
        limit: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[TopProduct]:
        logger.debug(
            "Building top products analytics: limit=%d, date_from=%s, date_to=%s",
            limit,
            date_from,
            date_to,
        )
        rows = await self._repository.get_top_products(
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )

        result = [
            TopProduct(
                product_id=row["_id"],
                product_name=row.get("product_name", ""),
                units_ordered=row.get("units_ordered", 0),
                orders_count=row.get("orders_count", 0),
                revenue=row.get("revenue", 0),
            )
            for row in rows
        ]
        logger.debug("Top products analytics built: products=%d", len(result))
        return result
