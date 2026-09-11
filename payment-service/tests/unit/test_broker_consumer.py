from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.broker.rabbitmq_consumer import RabbitMQConsumer
from app.core.config import PaymentCommandsExchangeSettings


@pytest.mark.asyncio
async def test_consumer_marks_failures_for_requeue() -> None:
    settings = PaymentCommandsExchangeSettings()
    message = SimpleNamespace(
        body=b'{"user_id": "user-id", "order_id": "order-id", "amount": 500}',
        routing_key=settings.create_routing_key,
        process=Mock(return_value=AsyncMock()),
    )
    payment_service = AsyncMock()
    consumer = RabbitMQConsumer(
        rabbitmq=AsyncMock(),
        payment_service=payment_service,
        commands_settings=settings,
        session=AsyncMock(),
    )

    await consumer._handle_payment_commands(message)

    message.process.assert_called_once_with(requeue=True)
    payment_service.create_payment.assert_awaited_once()


@pytest.mark.asyncio
async def test_consumer_discards_malformed_command() -> None:
    settings = PaymentCommandsExchangeSettings()
    message = SimpleNamespace(
        body=b"not-json",
        routing_key=settings.create_routing_key,
        process=Mock(return_value=AsyncMock()),
    )
    payment_service = AsyncMock()
    session = AsyncMock()
    consumer = RabbitMQConsumer(
        rabbitmq=AsyncMock(),
        payment_service=payment_service,
        commands_settings=settings,
        session=session,
    )

    await consumer._handle_payment_commands(message)

    payment_service.create_payment.assert_not_awaited()
    session.rollback.assert_not_awaited()
