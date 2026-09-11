from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.broker.consumer import RabbitMQConsumer
from app.core.config import CatalogCommandsExchangeSettings


@pytest.mark.asyncio
async def test_consumer_requeues_transient_processing_failures() -> None:
    settings = CatalogCommandsExchangeSettings()
    message = SimpleNamespace(
        body=b'{"order_id": "order-id", "items": []}',
        routing_key=settings.reserve_routing_key,
        process=Mock(return_value=AsyncMock()),
    )
    inventory_service = AsyncMock()
    consumer = RabbitMQConsumer(
        rabbitmq=AsyncMock(),
        inventory_service=inventory_service,
        commands_settings=settings,
        session=AsyncMock(),
    )

    await consumer._handle_command(message)

    message.process.assert_called_once_with(requeue=True)
    inventory_service.reserve.assert_awaited_once()


@pytest.mark.asyncio
async def test_consumer_discards_malformed_command() -> None:
    settings = CatalogCommandsExchangeSettings()
    message = SimpleNamespace(
        body=b"not-json",
        routing_key=settings.reserve_routing_key,
        process=Mock(return_value=AsyncMock()),
    )
    inventory_service = AsyncMock()
    session = AsyncMock()
    consumer = RabbitMQConsumer(
        rabbitmq=AsyncMock(),
        inventory_service=inventory_service,
        commands_settings=settings,
        session=session,
    )

    await consumer._handle_command(message)

    inventory_service.reserve.assert_not_awaited()
    session.rollback.assert_not_awaited()
