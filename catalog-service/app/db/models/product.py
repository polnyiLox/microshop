from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Product(Base):
    __tablename__ = "products"

    name: Mapped[str]
    description: Mapped[str] = mapped_column(
        Text
    )
    price: Mapped[int]
    quantity: Mapped[int]
    image_key: Mapped[str | None]
    category: Mapped[str]
    seller_id: Mapped[str] = mapped_column(index=True)
