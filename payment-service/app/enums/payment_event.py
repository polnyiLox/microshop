from enum import StrEnum


class PaymentAnalyticsEventTypeEnum(StrEnum):
    CREATED = "payment.created"
    SUCCEEDED = "payment.succeeded"
    FAILED = "payment.failed"
    CANCELLED = "payment.cancelled"
    REFUNDED = "payment.refunded"
