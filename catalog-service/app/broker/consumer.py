import json
import logging

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import CatalogCommandsExchangeSettings
from app.services import InventoryService

from .exchanges import declare_catalog_commands_queue
from .rabbitmq import RabbitMQClient


logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    """Route inventory commands while keeping database failures retryable."""

    def __init__(
        self,
        rabbitmq: RabbitMQClient,
        inventory_service: InventoryService,
        commands_settings: CatalogCommandsExchangeSettings,
        session: AsyncSession,
    ) -> None:
        self._rabbitmq = rabbitmq
        self._inventory_service = inventory_service
        self._commands_settings = commands_settings
        self._session = session

    async def _handle_command(self, message: AbstractIncomingMessage) -> None:
        try:
            async with message.process(requeue=True):
                try:
                    command = json.loads(message.body.decode())
                    logger.debug("Processing catalog command: routing_key=%s", message.routing_key)
                    if message.routing_key == self._commands_settings.reserve_routing_key:
                        await self._inventory_service.reserve(command)
                    elif message.routing_key == self._commands_settings.release_routing_key:
                        await self._inventory_service.release(command)
                    elif message.routing_key == self._commands_settings.confirm_routing_key:
                        await self._inventory_service.confirm(command)
                    else:
                        logger.warning("Unsupported catalog command: routing_key=%s", message.routing_key)
                except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                    logger.warning(
                        "Discarding malformed catalog command: routing_key=%s",
                        message.routing_key,
                        exc_info=True,
                    )
        except Exception:
            logger.exception("Catalog command failed: routing_key=%s", message.routing_key)
            await self._session.rollback()
            raise

    async def start_consuming(self) -> None:
        logger.info("Starting catalog command consumer")
        channel = await self._rabbitmq.get_channel()
        await channel.set_qos(prefetch_count=1)
        queue = await declare_catalog_commands_queue(
            channel,
            self._commands_settings,
        )
        await queue.consume(self._handle_command)
        logger.info("Catalog command consumer started")
