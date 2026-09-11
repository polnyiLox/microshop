import json
import logging

from aio_pika import DeliveryMode, Message

from app.core.config import CatalogEventsExchangeSettings

from .exchanges import declare_exchange
from .rabbitmq import RabbitMQClient


logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(
        self,
        rabbitmq: RabbitMQClient,
        exchange_settings: CatalogEventsExchangeSettings,
    ) -> None:
        self._rabbitmq = rabbitmq
        self._exchange_settings = exchange_settings

    async def publish(self, routing_key: str, event: dict) -> None:
        logger.debug("Publishing catalog event: routing_key=%s", routing_key)
        channel = await self._rabbitmq.get_channel()
        exchange = await declare_exchange(channel, self._exchange_settings)
        await exchange.publish(
            Message(json.dumps(event, default=str).encode(), content_type="application/json", delivery_mode=DeliveryMode.PERSISTENT),
            routing_key=routing_key,
        )
        logger.debug("Catalog event published: routing_key=%s", routing_key)
