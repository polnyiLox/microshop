from datetime import datetime

from pymongo.asynchronous.database import AsyncDatabase

from app.enums import RevenueGroupByEnum


class AnalyticsRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._collection = database["analytics_events"]

    async def get_overview(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, int]:
        match = self._build_date_match(date_from, date_to)

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "orders_total": self._count_event("order.created"),
                    "successful_payments": self._count_event("payment.succeeded"),
                    "failed_payments": self._count_event("payment.failed"),
                    "cancelled_payments": self._count_event("payment.cancelled"),
                    "refunded_payments": self._count_event("payment.refunded"),
                    "gross_revenue": self._sum_amount("payment.succeeded"),
                    "refunded_amount": self._sum_amount("payment.refunded"),
                }
            },
        ]

        cursor = await self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)
        if not results:
            return {}

        results[0].pop("_id", None)
        return results[0]

    async def get_orders(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        match = self._build_date_match(date_from, date_to)
        match["event_type"] = {
            "$in": [
                "order.created",
                "order.status_changed",
                "order.cancelled",
                "order.failed",
            ]
        }

        pipeline = [
            {"$match": match},
            {
                "$facet": {
                    "created": [
                        {"$match": {"event_type": "order.created"}},
                        {
                            "$group": {
                                "_id": None,
                                "orders_total": {"$sum": 1},
                                "average_order_value": {
                                    "$avg": {"$ifNull": ["$payload.total_amount", 0]}
                                },
                            }
                        },
                    ],
                    "statuses": [
                        {"$sort": {"occurred_at": 1}},
                        {
                            "$group": {
                                "_id": "$payload.order_id",
                                "status": {"$last": "$payload.status"},
                            }
                        },
                        {
                            "$match": {
                                "_id": {"$ne": None},
                                "status": {"$ne": None},
                            }
                        },
                        {
                            "$group": {
                                "_id": "$status",
                                "count": {"$sum": 1},
                            }
                        },
                    ],
                }
            },
        ]

        cursor = await self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)
        return results[0] if results else {"created": [], "statuses": []}

    async def get_payments(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, int]:
        match = self._build_date_match(date_from, date_to)
        match["event_type"] = {"$regex": "^payment\\."}

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "payments_total": self._count_event("payment.created"),
                    "successful_payments": self._count_event("payment.succeeded"),
                    "failed_payments": self._count_event("payment.failed"),
                    "cancelled_payments": self._count_event("payment.cancelled"),
                    "refunded_payments": self._count_event("payment.refunded"),
                    "gross_revenue": self._sum_amount("payment.succeeded"),
                    "refunded_amount": self._sum_amount("payment.refunded"),
                }
            },
        ]

        cursor = await self._collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)
        if not results:
            return {}

        results[0].pop("_id", None)
        return results[0]

    async def get_revenue(
        self,
        group_by: RevenueGroupByEnum,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        match = self._build_date_match(date_from, date_to)
        match["event_type"] = {
            "$in": ["payment.succeeded", "payment.refunded"]
        }

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": {
                        "$dateTrunc": {
                            "date": "$occurred_at",
                            "unit": group_by.value,
                        }
                    },
                    "successful_payments": self._count_event("payment.succeeded"),
                    "gross_revenue": self._sum_amount("payment.succeeded"),
                    "refunded_amount": self._sum_amount("payment.refunded"),
                }
            },
            {"$sort": {"_id": 1}},
        ]

        cursor = await self._collection.aggregate(pipeline)
        return await cursor.to_list(length=None)

    async def get_top_products(
        self,
        limit: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        match = self._build_date_match(date_from, date_to)
        match["event_type"] = "order.created"

        pipeline = [
            {"$match": match},
            {"$unwind": "$payload.items"},
            {
                "$group": {
                    "_id": "$payload.items.product_id",
                    "product_name": {"$last": "$payload.items.product_name"},
                    "units_ordered": {"$sum": "$payload.items.quantity"},
                    "orders_count": {"$sum": 1},
                    "revenue": {
                        "$sum": {
                            "$multiply": [
                                "$payload.items.quantity",
                                "$payload.items.unit_price",
                            ]
                        }
                    },
                }
            },
            {"$sort": {"units_ordered": -1, "revenue": -1}},
            {"$limit": limit},
        ]

        cursor = await self._collection.aggregate(pipeline)
        return await cursor.to_list(length=limit)

    @staticmethod
    def _build_date_match(
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> dict:
        match = {}
        occurred_at_filter = {}

        if date_from is not None:
            occurred_at_filter["$gte"] = date_from
        if date_to is not None:
            occurred_at_filter["$lte"] = date_to
        if occurred_at_filter:
            match["occurred_at"] = occurred_at_filter

        return match

    @staticmethod
    def _count_event(event_type: str) -> dict:
        return {
            "$sum": {
                "$cond": [
                    {"$eq": ["$event_type", event_type]},
                    1,
                    0,
                ]
            }
        }

    @staticmethod
    def _sum_amount(event_type: str) -> dict:
        return {
            "$sum": {
                "$cond": [
                    {"$eq": ["$event_type", event_type]},
                    {"$ifNull": ["$payload.amount", 0]},
                    0,
                ]
            }
        }
