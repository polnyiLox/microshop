from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Order, OrderItem


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all_by_user_id(self, user_id: str) -> list[Order]:
        query = (select(Order).where(Order.user_id == user_id)
                    .options(selectinload(Order.items)))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_all_by_seller_id(self, seller_id: str) -> list[Order]:
        query = (
            select(Order)
            .join(OrderItem)
            .where(OrderItem.seller_id == seller_id)
            .options(selectinload(Order.items))
            .distinct()
            .order_by(Order.created_at.desc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, order_id: str) -> Order | None:
        query = (select(Order).where(Order.id == order_id)
            .options(selectinload(Order.items)))
        return await self._session.scalar(query)

    async def create(self, user_id: str, total_amount: int) -> Order:
        new_order = Order(
            user_id=user_id,
            total_amount=total_amount
        )
        self._session.add(new_order)
        await self._session.flush()
        return new_order

    async def calculate_total_amount(self, order_id: str) -> int:
        query = select(
            func.coalesce(func.sum(OrderItem.unit_price * OrderItem.quantity), 0)
        ).where(OrderItem.order_id == order_id)
        return await self._session.scalar(query)

    async def delete(self, order: Order) -> None:
        await self._session.delete(order)
        await self._session.flush()
