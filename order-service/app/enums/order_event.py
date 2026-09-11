from enum import StrEnum


class OrderAnalyticsEventTypeEnum(StrEnum):
    CREATED = "order.created"
    STATUS_CHANGED = "order.status_changed"
    CANCELLED = "order.cancelled"
    FAILED = "order.failed"
