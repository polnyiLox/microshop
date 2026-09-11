import logging
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import RedisCache
from app.core.config import Settings
from app.exceptions import (
    BalanceReferenceConflictError,
    InsufficientBalanceError,
    UserNotFoundError,
)
from app.repositories import BalanceOperationRepository, UserRepository
from app.schemas import BalanceRead


logger = logging.getLogger(__name__)


class BalanceService:
    """Apply serialized, idempotent changes to a user's balance."""

    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
        operation_repo: BalanceOperationRepository,
        redis_cache: RedisCache,
        settings: Settings,
    ) -> None:
        self._session = session
        self._user_repo = user_repo
        self._operation_repo = operation_repo
        self._redis_cache = redis_cache
        self._settings = settings

    async def get_balance(self, user_id: str) -> BalanceRead:
        logger.debug("Reading balance user_id=%s", user_id)
        cache_key = self._redis_cache.create_balance_key(user_id)
        cached_balance = await self._redis_cache.get(cache_key)
        if cached_balance is not None:
            logger.debug("Balance cache hit user_id=%s", user_id)
            try:
                return BalanceRead.model_validate_json(cached_balance)
            except ValidationError:
                logger.warning("Invalid cached balance user_id=%s", user_id)
                await self._redis_cache.delete(cache_key)
        else:
            logger.debug("Balance cache miss user_id=%s", user_id)

        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            logger.warning("Balance user not found user_id=%s", user_id)
            raise UserNotFoundError()
        balance = BalanceRead(balance=user.balance)
        await self._redis_cache.set(
            cache_key,
            balance.model_dump_json(),
            self._settings.redis.ttl_seconds,
        )
        return balance

    async def _change_balance(
        self,
        user_id: str,
        amount_delta: int,
        reference: str,
    ) -> BalanceRead:
        existing = await self._operation_repo.get_by_reference(reference)
        if existing is not None:
            if existing.user_id != user_id or existing.amount_delta != amount_delta:
                logger.warning(
                    "Balance reference conflict user_id=%s reference=%s",
                    user_id,
                    reference,
                )
                raise BalanceReferenceConflictError()
            logger.debug(
                "Returning idempotent balance operation user_id=%s reference=%s",
                user_id,
                reference,
            )
            return BalanceRead(balance=existing.balance_after)

        user = await self._user_repo.get_by_id_for_update(user_id)
        if user is None:
            logger.warning("Balance user not found user_id=%s", user_id)
            raise UserNotFoundError()

        balance_after = user.balance + amount_delta
        if balance_after < 0:
            logger.warning(
                "Balance change rejected user_id=%s amount_delta=%s",
                user_id,
                amount_delta,
            )
            raise InsufficientBalanceError()

        user.balance = balance_after
        await self._operation_repo.create(
            user_id=user_id,
            reference=reference,
            amount_delta=amount_delta,
            balance_after=balance_after,
        )
        await self._session.commit()
        await self._redis_cache.delete(
            self._redis_cache.create_balance_key(user_id)
        )
        logger.info(
            "Balance changed user_id=%s amount_delta=%s balance_after=%s reference=%s",
            user_id,
            amount_delta,
            balance_after,
            reference,
        )
        return BalanceRead(balance=balance_after)

    async def deposit(self, user_id: str, amount: int) -> BalanceRead:
        logger.info("Starting balance deposit user_id=%s amount=%s", user_id, amount)
        return await self._change_balance(
            user_id=user_id,
            amount_delta=amount,
            reference=f"manual-deposit:{uuid4()}",
        )

    async def withdraw(self, user_id: str, amount: int) -> BalanceRead:
        logger.info("Starting balance withdrawal user_id=%s amount=%s", user_id, amount)
        return await self._change_balance(
            user_id=user_id,
            amount_delta=-amount,
            reference=f"manual-withdraw:{uuid4()}",
        )

    async def credit(
        self,
        user_id: str,
        amount: int,
        reference: str,
    ) -> BalanceRead:
        logger.info("Starting balance credit user_id=%s amount=%s", user_id, amount)
        return await self._change_balance(user_id, amount, reference)

    async def debit(
        self,
        user_id: str,
        amount: int,
        reference: str,
    ) -> BalanceRead:
        logger.info("Starting balance debit user_id=%s amount=%s", user_id, amount)
        return await self._change_balance(user_id, -amount, reference)
