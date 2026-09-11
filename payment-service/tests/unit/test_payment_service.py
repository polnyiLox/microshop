from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.config import PaymentEventsExchangeSettings
from app.enums import PaymentStatusEnum
from app.exceptions import InsufficientBalanceError, InvalidPaymentStatusTransitionError
from app.schemas import PaymentCreate, PaymentRead, PaymentStatusUpdate
from app.services import PaymentService


def payment(status: PaymentStatusEnum = PaymentStatusEnum.PENDING):
    return SimpleNamespace(
        id="payment-id",
        user_id="user-id",
        order_id="order-id",
        amount=500,
        status=status,
        created_at=datetime.now(UTC),
    )


def build_service():
    repository = AsyncMock()
    session = AsyncMock()
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
    return service, repository, session, publisher, kafka, cache


@pytest.mark.asyncio
async def test_create_returns_existing_active_payment_idempotently() -> None:
    service, repository, session, publisher, _, _ = build_service()
    repository.get_by_order_id_for_statuses.return_value = payment(
        PaymentStatusEnum.SUCCEEDED
    )

    result = await service.create_payment(PaymentCreate(
        user_id="user-id",
        order_id="order-id",
        amount=500,
    ))

    assert result.id == "payment-id"
    repository.create.assert_not_awaited()
    session.commit.assert_not_awaited()
    publisher.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_status_transition_does_not_persist() -> None:
    service, repository, session, _, _, _ = build_service()
    repository.get_by_id.return_value = payment(PaymentStatusEnum.PENDING)

    with pytest.raises(InvalidPaymentStatusTransitionError):
        await service.update_payment_status(
            "payment-id",
            PaymentStatusUpdate(status=PaymentStatusEnum.SUCCEEDED),
        )

    repository.update_status.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_terminal_status_publishes_rabbit_and_kafka_events() -> None:
    service, repository, session, publisher, kafka, cache = build_service()
    current = payment(PaymentStatusEnum.PROCESSING)
    repository.get_by_id.return_value = current

    async def update_status(instance, status):
        instance.status = status
        return instance

    repository.update_status.side_effect = update_status
    result = await service.update_payment_status(
        "payment-id",
        PaymentStatusUpdate(status=PaymentStatusEnum.SUCCEEDED),
    )

    assert result.status == PaymentStatusEnum.SUCCEEDED
    session.commit.assert_awaited_once()
    publisher.publish.assert_awaited_once()
    kafka.publish.assert_awaited_once()
    cache.delete.assert_awaited_once_with(
        "payment:payment-id",
        "order:order-id",
        "user:user-id",
    )


@pytest.mark.asyncio
async def test_complete_moves_pending_payment_through_processing() -> None:
    service, repository, _, _, _, _ = build_service()
    repository.get_by_id.return_value = payment(PaymentStatusEnum.PENDING)
    service.update_payment_status = AsyncMock(side_effect=[
        payment(PaymentStatusEnum.PROCESSING),
        payment(PaymentStatusEnum.SUCCEEDED),
    ])

    with patch("app.services.payment.asyncio.sleep", new=AsyncMock()) as sleep:
        result = await service.complete_payment("payment-id")

    assert result.status == PaymentStatusEnum.SUCCEEDED
    assert service.update_payment_status.await_count == 2
    service._balance_client.debit.assert_awaited_once_with(
        user_id="user-id",
        amount=500,
        reference="payment:payment-id",
    )
    sleep.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_complete_marks_payment_failed_for_insufficient_balance() -> None:
    service, repository, _, _, _, _ = build_service()
    repository.get_by_id.return_value = payment(PaymentStatusEnum.PENDING)
    service._balance_client.debit.side_effect = InsufficientBalanceError()
    service.update_payment_status = AsyncMock(side_effect=[
        payment(PaymentStatusEnum.PROCESSING),
        payment(PaymentStatusEnum.FAILED),
    ])

    result = await service.complete_payment("payment-id")

    assert result.status == PaymentStatusEnum.FAILED
    assert service.update_payment_status.await_count == 2


@pytest.mark.asyncio
async def test_retry_creates_payment_after_failure() -> None:
    service, repository, _, _, _, _ = build_service()
    repository.get_by_id.return_value = payment(PaymentStatusEnum.FAILED)
    new_payment = payment(PaymentStatusEnum.PENDING)
    new_payment.id = "new-payment-id"
    service.create_payment = AsyncMock(return_value=new_payment)
    service.complete_payment = AsyncMock(
        return_value=payment(PaymentStatusEnum.SUCCEEDED),
    )

    result = await service.retry_payment("payment-id")

    assert result.status == PaymentStatusEnum.SUCCEEDED
    service.create_payment.assert_awaited_once()
    service.complete_payment.assert_awaited_once_with("new-payment-id")


@pytest.mark.asyncio
async def test_get_payment_returns_cached_value() -> None:
    service, repository, _, _, _, cache = build_service()
    cache.get.return_value = PaymentRead.model_validate(payment()).model_dump_json()

    result = await service.get_payment_by_id("payment-id")

    assert result.id == "payment-id"
    repository.get_by_id.assert_not_awaited()
