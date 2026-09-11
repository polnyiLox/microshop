from pydantic import BaseModel, ConfigDict, Field


class OrderItemBase(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemUpdate(BaseModel):
    quantity: int | None = Field(None, gt=0)


class OrderItemRead(OrderItemBase):
    id: str
    order_id: str
    seller_id: str
    product_name: str
    unit_price: int

    model_config = ConfigDict(
        from_attributes=True
    )
