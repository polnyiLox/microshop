from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.exceptions import BalanceReferenceConflictError, InsufficientBalanceError
from app.services import BalanceService


def build_service():
    session = AsyncMock()
    users = AsyncMock()
    operations = AsyncMock()
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_balance_key = Mock(side_effect=lambda user_id: f"balance:{user_id}")
    settings = SimpleNamespace(redis=SimpleNamespace(ttl_seconds=60))
    service = BalanceService(session, users, operations, cache, settings)
    return service, session, users, operations, cache


@pytest.mark.asyncio
async def test_debit_updates_locked_user_balance() -> None:
    service, session, users, operations, cache = build_service()
    users.get_by_id_for_update.return_value = SimpleNamespace(balance=1000)
    operations.get_by_reference.return_value = None

    result = await service.debit("user-id", 300, "payment:1")

    assert result.balance == 700
    operations.create.assert_awaited_once_with(
        user_id="user-id",
        reference="payment:1",
        amount_delta=-300,
        balance_after=700,
    )
    session.commit.assert_awaited_once()
    cache.delete.assert_awaited_once_with("balance:user-id")


@pytest.mark.asyncio
async def test_debit_rejects_insufficient_balance() -> None:
    service, session, users, operations, _ = build_service()
    users.get_by_id_for_update.return_value = SimpleNamespace(balance=100)
    operations.get_by_reference.return_value = None

    with pytest.raises(InsufficientBalanceError):
        await service.debit("user-id", 300, "payment:1")

    operations.create.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_repeated_reference_returns_original_result() -> None:
    service, session, users, operations, _ = build_service()
    operations.get_by_reference.return_value = SimpleNamespace(
        user_id="user-id",
        amount_delta=-300,
        balance_after=700,
    )

    result = await service.debit("user-id", 300, "payment:1")

    assert result.balance == 700
    users.get_by_id_for_update.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_reused_reference_with_different_amount_is_rejected() -> None:
    service, _, _, operations, _ = build_service()
    operations.get_by_reference.return_value = SimpleNamespace(
        user_id="user-id",
        amount_delta=-200,
        balance_after=800,
    )

    with pytest.raises(BalanceReferenceConflictError):
        await service.debit("user-id", 300, "payment:1")


@pytest.mark.asyncio
async def test_get_balance_returns_cached_value() -> None:
    service, _, users, _, cache = build_service()
    cache.get.return_value = '{"balance":700}'

    result = await service.get_balance("user-id")

    assert result.balance == 700
    users.get_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_balance_caches_database_value() -> None:
    service, _, users, _, cache = build_service()
    users.get_by_id.return_value = SimpleNamespace(balance=700)

    result = await service.get_balance("user-id")

    assert result.balance == 700
    cache.set.assert_awaited_once_with("balance:user-id", '{"balance":700}', 60)
