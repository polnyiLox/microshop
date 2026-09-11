import logging

import httpx

from app.exceptions import BalanceServiceUnavailableError, InsufficientBalanceError


logger = logging.getLogger(__name__)


class BalanceClient:
    """Apply idempotent wallet operations through auth-service."""

    def __init__(self, base_url: str, internal_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-Internal-Token": internal_token}

    async def _change_balance(
        self,
        user_id: str,
        operation: str,
        amount: int,
        reference: str,
    ) -> None:
        logger.debug(
            "Calling balance service: user_id=%s, operation=%s, amount=%d",
            user_id,
            operation,
            amount,
        )
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(
                    f"{self._base_url}/users/{user_id}/balance/{operation}",
                    headers=self._headers,
                    json={"amount": amount, "reference": reference},
                )
            if response.status_code == 409:
                logger.warning(
                    "Balance operation rejected: user_id=%s, operation=%s",
                    user_id,
                    operation,
                )
                raise InsufficientBalanceError()
            response.raise_for_status()
            logger.debug(
                "Balance service call completed: user_id=%s, operation=%s",
                user_id,
                operation,
            )
        except InsufficientBalanceError:
            raise
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.error(
                "Balance service unavailable: user_id=%s, operation=%s, error=%s",
                user_id,
                operation,
                exc,
            )
            raise BalanceServiceUnavailableError() from exc

    async def debit(self, user_id: str, amount: int, reference: str) -> None:
        await self._change_balance(user_id, "debit", amount, reference)

    async def credit(self, user_id: str, amount: int, reference: str) -> None:
        await self._change_balance(user_id, "credit", amount, reference)
