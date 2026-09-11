from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Payment
from app.enums import PaymentStatusEnum


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, payment_id: str) -> Payment | None:
        query = select(Payment).where(Payment.id == payment_id)
        return await self._session.scalar(query)

    async def get_all_by_order_id(self, order_id: str) -> list[Payment]:
        query = (
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_order_id_for_statuses(
        self,
        order_id: str,
        statuses: set[PaymentStatusEnum],
    ) -> Payment | None:
        query = (
            select(Payment)
            .where(
                Payment.order_id == order_id,
                Payment.status.in_(statuses),
            )
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
        return await self._session.scalar(query)

    async def get_all_by_user_id(self, user_id: str) -> list[Payment]:
        query = (
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
                )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create(self, order_id: str, amount: int, user_id: str) -> Payment:
        payment = Payment(order_id=order_id, amount=amount, user_id=user_id)
        self._session.add(payment)
        await self._session.flush()
        return payment

    async def update_status(
        self,
        payment: Payment,
        status: PaymentStatusEnum,
    ) -> Payment:
        payment.status = status
        await self._session.flush()
        return payment
