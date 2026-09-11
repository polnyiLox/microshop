from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from app.enums import OrderStatusEnum

from .order_item import OrderItemCreate, OrderItemRead
    

class OrderCreate(BaseModel):
    user_id: str
    items: list[OrderItemCreate] = Field(default_factory=list)


class OrderCreateRequest(BaseModel):
    items: list[OrderItemCreate] = Field(default_factory=list)


class OrderUpdate(BaseModel):
    status: OrderStatusEnum | None = None


class OrderUpdateAllItems(BaseModel):
    items: list[OrderItemCreate]


class OrderRead(BaseModel):
    id: str
    user_id: str
    status: OrderStatusEnum
    total_amount: int
    created_at: datetime
    items: list[OrderItemRead]

    model_config = ConfigDict(
        from_attributes=True
    )
