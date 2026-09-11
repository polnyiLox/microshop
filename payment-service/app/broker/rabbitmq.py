import logging

from aio_pika import connect_robust
from aio_pika.abc import AbstractRobustChannel, AbstractRobustConnection

from app.core.config import RabbitMQSettings


logger = logging.getLogger(__name__)


class RabbitMQClient:
    """Manages the shared RabbitMQ connection for the application."""

    def __init__(self, settings: RabbitMQSettings) -> None:
        self._settings = settings
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractRobustChannel | None = None

    async def connect(self) -> None:
        """Open one robust connection with one channel when needed."""
        if self._connection is not None and not self._connection.is_closed:
            logger.debug("RabbitMQ connection is already open")
            return

        logger.info("Connecting payment-service to RabbitMQ")
        self._connection = await connect_robust(self._settings.url)
        self._channel = await self._connection.channel()
        logger.info("Payment-service connected to RabbitMQ")

    async def get_channel(self) -> AbstractRobustChannel:
        """Return the application channel, opening it lazily if necessary."""
        await self.connect()
        assert self._channel is not None
        return self._channel

    async def close(self) -> None:
        """Close the connection when the FastAPI application stops."""
        if self._connection is not None and not self._connection.is_closed:
            logger.info("Closing payment-service RabbitMQ connection")
            await self._connection.close()
            logger.info("Payment-service RabbitMQ connection closed")

        self._channel = None
        self._connection = None
