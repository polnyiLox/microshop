from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from app.enums import PaymentAnalyticsEventTypeEnum, PaymentStatusEnum


class PaymentAnalyticsEventPayload(BaseModel):
    payment_id: str
    order_id: str
    user_id: str
    amount: int
    status: PaymentStatusEnum


class PaymentAnalyticsEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: PaymentAnalyticsEventTypeEnum
    event_version: int = 1
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    producer: str = "payment-service"
    payload: PaymentAnalyticsEventPayload
