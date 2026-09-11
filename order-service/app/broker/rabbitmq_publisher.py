import json
import logging

from aio_pika import Message, DeliveryMode

from app.core.config import ExchangeSettings

from .rabbitmq_exchanges import declare_exchange
from .rabbitmq import RabbitMQClient


logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self, rabbitmq: RabbitMQClient) -> None:
        self._rabbitmq = rabbitmq

    async def publish(
        self,
        exchange_settings: ExchangeSettings,
        routing_key: str,
        event: dict,
    ) -> None:
        logger.debug("Publishing RabbitMQ event: routing_key=%s", routing_key)
        channel = await self._rabbitmq.get_channel()
        exchange = await declare_exchange(channel, exchange_settings)
        message = Message(
            body=json.dumps(event).encode(),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=routing_key)
        logger.debug("RabbitMQ event published: routing_key=%s", routing_key)
