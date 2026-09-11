from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OrderItem


class OrderItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all_by_order_id(self, order_id: str) -> list[OrderItem]:
        query = select(OrderItem).where(OrderItem.order_id == order_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, order_item_id: str) -> OrderItem | None:
        query = select(OrderItem).where(OrderItem.id == order_item_id)
        return await self._session.scalar(query)

    async def create(
            self, 
            order_id: str, 
            product_id: str, 
            seller_id: str,
            product_name: str, 
            quantity: int, 
            unit_price: int
    ) -> OrderItem:
        new_order_item = OrderItem(
            order_id=order_id,
            product_id=product_id,
            seller_id=seller_id,
            product_name=product_name,
            quantity=quantity,
            unit_price=unit_price
        )
        self._session.add(new_order_item)
        await self._session.flush()
        return new_order_item

    async def delete(self, order_item: OrderItem) -> None:
        await self._session.delete(order_item)
        await self._session.flush()

    async def delete_all_by_order_id(self, order_id: str) -> None:
        stmt = delete(OrderItem).where(OrderItem.order_id == order_id)
        await self._session.execute(stmt)
        await self._session.flush()
