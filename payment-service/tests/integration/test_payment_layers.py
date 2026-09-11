from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PaymentEventsExchangeSettings
from app.enums import PaymentStatusEnum
from app.repositories import PaymentRepository
from app.schemas import PaymentCreate, PaymentStatusUpdate
from app.services import PaymentService


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_repository_filters_payment_by_status(session: AsyncSession) -> None:
    repository = PaymentRepository(session)
    created = await repository.create("order-id", 100, "user-id")
    await session.commit()

    pending = await repository.get_by_order_id_for_statuses(
        "order-id", {PaymentStatusEnum.PENDING}
    )
    missing = await repository.get_by_order_id_for_statuses(
        "order-id", {PaymentStatusEnum.SUCCEEDED}
    )

    assert pending is not None and pending.id == created.id
    assert missing is None


async def test_service_creates_and_updates_payment_in_postgres(session: AsyncSession) -> None:
    repository = PaymentRepository(session)
    publisher = AsyncMock()
    kafka = AsyncMock()
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_payment_key = Mock(side_effect=lambda payment_id: f"payment:{payment_id}")
    cache.create_order_payments_key = Mock(side_effect=lambda order_id: f"order:{order_id}")
    cache.create_user_payments_key = Mock(side_effect=lambda user_id: f"user:{user_id}")
    service = PaymentService(
        repository,
        session,
        publisher,
        kafka,
        AsyncMock(),
        PaymentEventsExchangeSettings(),
        cache,
        60,
    )

    created = await service.create_payment(PaymentCreate(
        user_id="service-user",
        order_id="service-order",
        amount=750,
    ))
    processing = await service.update_payment_status(
        created.id,
        PaymentStatusUpdate(status=PaymentStatusEnum.PROCESSING),
    )

    assert processing.status == PaymentStatusEnum.PROCESSING
    assert (await repository.get_by_id(created.id)).status == PaymentStatusEnum.PROCESSING
    publisher.publish.assert_awaited_once()


async def test_service_completes_payment_and_persists_status(
    session: AsyncSession,
) -> None:
    repository = PaymentRepository(session)
    publisher = AsyncMock()
    kafka = AsyncMock()
    balance = AsyncMock()
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_payment_key = Mock(
        side_effect=lambda payment_id: f"payment:{payment_id}",
    )
    cache.create_order_payments_key = Mock(
        side_effect=lambda order_id: f"order:{order_id}",
    )
    cache.create_user_payments_key = Mock(
        side_effect=lambda user_id: f"user:{user_id}",
    )
    service = PaymentService(
        repository,
        session,
        publisher,
        kafka,
        balance,
        PaymentEventsExchangeSettings(),
        cache,
        60,
    )
    created = await service.create_payment(PaymentCreate(
        user_id="completion-user",
        order_id="completion-order",
        amount=900,
    ))

    with patch("app.services.payment.asyncio.sleep", new_callable=AsyncMock):
        completed = await service.complete_payment(created.id)

    stored = await repository.get_by_id(created.id)
    assert completed.status == PaymentStatusEnum.SUCCEEDED
    assert stored is not None
    assert stored.status == PaymentStatusEnum.SUCCEEDED
    balance.debit.assert_awaited_once_with(
        user_id="completion-user",
        amount=900,
        reference=f"payment:{created.id}",
    )
    assert publisher.publish.await_count == 2
    assert kafka.publish.await_count == 2
