from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import PaymentStatusEnum


class PaymentCreate(BaseModel):
    user_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    amount: int = Field(gt=0)


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatusEnum


class PaymentRead(BaseModel):
    id: str
    user_id: str
    order_id: str
    status: PaymentStatusEnum
    amount: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
