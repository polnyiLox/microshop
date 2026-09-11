from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.routers.v1.payment import create_payment, get_payments, require_payment_owner
from app.enums import PaymentStatusEnum
from app.exceptions import PaymentNotFoundError
from app.schemas import PaymentCreate


def payment(user_id: str):
    return SimpleNamespace(
        id="payment-id",
        user_id=user_id,
        order_id="order-id",
        amount=100,
        status=PaymentStatusEnum.PENDING,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_create_uses_trusted_header_identity() -> None:
    service = AsyncMock()
    service.create_payment.return_value = payment("trusted-user")

    await create_payment(
        PaymentCreate(user_id="spoofed-user", order_id="order-id", amount=100),
        "trusted-user",
        service,
    )

    sent = service.create_payment.await_args.kwargs["payment_data"]
    assert sent.user_id == "trusted-user"


@pytest.mark.asyncio
async def test_list_filters_foreign_payments() -> None:
    service = AsyncMock()
    service.get_payments_by_order_id.return_value = [
        payment("trusted-user"),
        payment("other-user"),
    ]

    result = await get_payments("order-id", "trusted-user", service)

    assert [item.user_id for item in result] == ["trusted-user"]


@pytest.mark.asyncio
async def test_owner_dependency_hides_foreign_payment() -> None:
    service = AsyncMock()
    service.get_payment_by_id.return_value = payment("other-user")

    with pytest.raises(PaymentNotFoundError):
        await require_payment_owner("payment-id", "trusted-user", service)
