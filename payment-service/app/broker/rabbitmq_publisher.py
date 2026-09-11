import json
import logging
from typing import Any

from aio_pika import DeliveryMode, Message

from app.core.config import PaymentEventsExchangeSettings

from .rabbitmq_exchanges import declare_payment_events_exchange
from .rabbitmq import RabbitMQClient


logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    """Publishes JSON events without containing payment business rules."""

    def __init__(
        self,
        rabbitmq: RabbitMQClient,
        exchange_settings: PaymentEventsExchangeSettings,
    ) -> None:
        self._rabbitmq = rabbitmq
        self._exchange_settings = exchange_settings

    async def publish(self, routing_key: str, payload: dict[str, Any]) -> None:
        logger.debug("Publishing RabbitMQ payment event: routing_key=%s", routing_key)
        channel = await self._rabbitmq.get_channel()
        exchange = await declare_payment_events_exchange(
            channel,
            self._exchange_settings,
        )
        message = Message(
            body=json.dumps(payload, default=str).encode(),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=routing_key)
        logger.debug("RabbitMQ payment event published: routing_key=%s", routing_key)
