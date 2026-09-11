from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.broker.consumer import RabbitMQConsumer
from app.core.config import OrderEventsExchangeSettings, PaymentEventsExchangeSettings


@pytest.mark.asyncio
async def test_order_consumer_marks_failures_for_requeue() -> None:
    order_settings = OrderEventsExchangeSettings()
    message = SimpleNamespace(
        body=b'{"user_id": "user-id", "order_id": "order-id"}',
        routing_key=order_settings.order_created_routing_key,
        process=Mock(return_value=AsyncMock()),
    )
    notification_service = AsyncMock()
    consumer = RabbitMQConsumer(
        rabbitmq=AsyncMock(),
        order_events_exchange_settings=order_settings,
        payment_events_exchange_settings=PaymentEventsExchangeSettings(),
        notification_service=notification_service,
        session=AsyncMock(),
    )

    await consumer._handle_order_events(message)

    message.process.assert_called_once_with(requeue=True)
    notification_service.create_notification.assert_awaited_once()


@pytest.mark.asyncio
async def test_order_consumer_discards_malformed_event() -> None:
    order_settings = OrderEventsExchangeSettings()
    message = SimpleNamespace(
        body=b"not-json",
        routing_key=order_settings.order_created_routing_key,
        process=Mock(return_value=AsyncMock()),
    )
    notification_service = AsyncMock()
    session = AsyncMock()
    consumer = RabbitMQConsumer(
        rabbitmq=AsyncMock(),
        order_events_exchange_settings=order_settings,
        payment_events_exchange_settings=PaymentEventsExchangeSettings(),
        notification_service=notification_service,
        session=session,
    )

    await consumer._handle_order_events(message)

    notification_service.create_notification.assert_not_awaited()
    session.rollback.assert_not_awaited()
