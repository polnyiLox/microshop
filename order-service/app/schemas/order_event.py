from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.enums import OrderAnalyticsEventTypeEnum, OrderStatusEnum


class OrderAnalyticsItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: int

    model_config = ConfigDict(from_attributes=True)


class OrderAnalyticsEventPayload(BaseModel):
    order_id: str
    user_id: str
    total_amount: int
    status: OrderStatusEnum
    previous_status: OrderStatusEnum | None = None
    items: list[OrderAnalyticsItem] = Field(default_factory=list)


class OrderAnalyticsEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: OrderAnalyticsEventTypeEnum
    event_version: int = 1
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    producer: str = "order-service"
    payload: OrderAnalyticsEventPayload
