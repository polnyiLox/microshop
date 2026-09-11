from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BalanceOperation


class BalanceOperationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_reference(self, reference: str) -> BalanceOperation | None:
        query = select(BalanceOperation).where(
            BalanceOperation.reference == reference,
        )
        return await self._session.scalar(query)

    async def create(
        self,
        user_id: str,
        reference: str,
        amount_delta: int,
        balance_after: int,
    ) -> BalanceOperation:
        operation = BalanceOperation(
            user_id=user_id,
            reference=reference,
            amount_delta=amount_delta,
            balance_after=balance_after,
        )
        self._session.add(operation)
        await self._session.flush()
        return operation
