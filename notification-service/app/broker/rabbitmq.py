import logging

import aio_pika
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel

from app.core.config import RabbitMQSettings


logger = logging.getLogger(__name__)


class RabbitMQClient:
    def __init__(self, settings: RabbitMQSettings) -> None:
        self._settings = settings
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractRobustChannel | None = None

    async def connect(self) -> None:
        if self._connection is not None and not self._connection.is_closed:
            logger.debug("RabbitMQ connection is already open")
            return

        logger.info("Connecting notification-service to RabbitMQ")
        self._connection = await aio_pika.connect_robust(self._settings.url)
        self._channel = await self._connection.channel()
        logger.info("Notification-service connected to RabbitMQ")
        
    async def get_channel(self) -> AbstractRobustChannel:
        await self.connect()
        assert self._channel is not None
        return self._channel

    async def close(self) -> None:
        if self._connection is not None and not self._connection.is_closed:
            logger.info("Closing notification-service RabbitMQ connection")
            await self._connection.close()
            logger.info("Notification-service RabbitMQ connection closed")

        self._connection = None
        self._channel = None
