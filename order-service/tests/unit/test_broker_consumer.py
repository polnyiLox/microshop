from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.broker.rabbitmq_consumer import RabbitMqConsumer
from app.core.config import CatalogEventsExchangeSettings, PaymentEventsExchangeSettings


@pytest.mark.asyncio
async def test_payment_consumer_marks_failures_for_requeue() -> None:
    payment_settings = PaymentEventsExchangeSettings()
    message = SimpleNamespace(
        body=b'{"order_id": "order-id"}',
        routing_key=payment_settings.payment_succeeded_routing_key,
        process=Mock(return_value=AsyncMock()),
    )
    order_service = AsyncMock()
    consumer = RabbitMqConsumer(
        rabbitmq=AsyncMock(),
        payment_events_settings=payment_settings,
        catalog_events_settings=CatalogEventsExchangeSettings(),
        order_service=order_service,
        session=AsyncMock(),
    )

    await consumer._handle_payment_events(message)

    message.process.assert_called_once_with(requeue=True)
    order_service.handle_payment_succeeded.assert_awaited_once()


@pytest.mark.asyncio
async def test_payment_consumer_discards_malformed_event() -> None:
    payment_settings = PaymentEventsExchangeSettings()
    message = SimpleNamespace(
        body=b"not-json",
        routing_key=payment_settings.payment_succeeded_routing_key,
        process=Mock(return_value=AsyncMock()),
    )
    order_service = AsyncMock()
    session = AsyncMock()
    consumer = RabbitMqConsumer(
        rabbitmq=AsyncMock(),
        payment_events_settings=payment_settings,
        catalog_events_settings=CatalogEventsExchangeSettings(),
        order_service=order_service,
        session=session,
    )

    await consumer._handle_payment_events(message)

    order_service.handle_payment_succeeded.assert_not_awaited()
    session.rollback.assert_not_awaited()
