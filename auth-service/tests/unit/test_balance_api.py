from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.routers.v1.balance import deposit_balance, get_balance, withdraw_balance
from app.api.routers.v1.internal import credit_balance, debit_balance
from app.schemas import BalanceAmount, InternalBalanceChange


@pytest.mark.asyncio
async def test_public_deposit_uses_authenticated_user() -> None:
    service = AsyncMock()
    user = SimpleNamespace(id="user-id")
    data = BalanceAmount(amount=500)

    await deposit_balance(data, user, service)

    service.deposit.assert_awaited_once_with("user-id", 500)


@pytest.mark.asyncio
async def test_public_withdraw_uses_authenticated_user() -> None:
    service = AsyncMock()
    user = SimpleNamespace(id="user-id")
    data = BalanceAmount(amount=200)

    await withdraw_balance(data, user, service)

    service.withdraw.assert_awaited_once_with("user-id", 200)


@pytest.mark.asyncio
async def test_public_balance_reads_authenticated_user() -> None:
    service = AsyncMock()
    user = SimpleNamespace(id="user-id")

    await get_balance(user, service)

    service.get_balance.assert_awaited_once_with("user-id")


@pytest.mark.asyncio
async def test_internal_debit_preserves_reference() -> None:
    service = AsyncMock()
    data = InternalBalanceChange(amount=300, reference="payment:1")

    await debit_balance("user-id", data, service)

    service.debit.assert_awaited_once_with("user-id", 300, "payment:1")


@pytest.mark.asyncio
async def test_internal_credit_preserves_reference() -> None:
    service = AsyncMock()
    data = InternalBalanceChange(amount=300, reference="payment-refund:1")

    await credit_balance("user-id", data, service)

    service.credit.assert_awaited_once_with("user-id", 300, "payment-refund:1")
