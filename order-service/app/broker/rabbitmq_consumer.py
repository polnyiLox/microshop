import asyncio
import json
import logging

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import CatalogEventsExchangeSettings, PaymentEventsExchangeSettings
from app.services import OrderService

from .rabbitmq_exchanges import declare_order_catalog_queue, declare_order_payment_queue
from .rabbitmq import RabbitMQClient


logger = logging.getLogger(__name__)


class RabbitMqConsumer:
    """Translate broker events into serialized order state transitions."""

    def __init__(
            self,
            rabbitmq: RabbitMQClient,
            payment_events_settings: PaymentEventsExchangeSettings,
            catalog_events_settings: CatalogEventsExchangeSettings,
            order_service: OrderService,
            session: AsyncSession,
    ) -> None:
        self._rabbitmq = rabbitmq
        self._payment_events_settings = payment_events_settings
        self._catalog_events_settings = catalog_events_settings
        self._order_service = order_service
        self._session = session
        self._processing_lock = asyncio.Lock()

    async def _handle_payment_events(self, message: AbstractIncomingMessage) -> None:
        async with self._processing_lock:
            try:
                async with message.process(requeue=True):
                    try:
                        event = json.loads(message.body.decode("utf-8"))
                        logger.debug("Processing payment event: routing_key=%s", message.routing_key)

                        if message.routing_key == self._payment_events_settings.payment_created_routing_key:
                            await self._order_service.handle_payment_created(event)
                        elif message.routing_key == self._payment_events_settings.payment_succeeded_routing_key:
                            await self._order_service.handle_payment_succeeded(event)
                        elif message.routing_key == self._payment_events_settings.payment_failed_routing_key:
                            await self._order_service.handle_payment_failed(event)
                        elif message.routing_key == self._payment_events_settings.payment_cancelled_routing_key:
                            await self._order_service.handle_payment_cancelled(event)
                        elif message.routing_key == self._payment_events_settings.payment_refunded_routing_key:
                            await self._order_service.handle_payment_refunded(event)
                    except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                        logger.warning(
                            "Discarding malformed payment event: routing_key=%s",
                            message.routing_key,
                            exc_info=True,
                        )
            except Exception:
                logger.exception("Payment event processing failed: routing_key=%s", message.routing_key)
                await self._session.rollback()
                raise

    async def _handle_catalog_events(self, message: AbstractIncomingMessage) -> None:
        async with self._processing_lock:
            try:
                async with message.process(requeue=True):
                    try:
                        event = json.loads(message.body.decode("utf-8"))
                        logger.debug("Processing catalog event: routing_key=%s", message.routing_key)
                        if message.routing_key == self._catalog_events_settings.reserved_routing_key:
                            await self._order_service.handle_inventory_reserved(event)
                        elif message.routing_key == self._catalog_events_settings.reservation_failed_routing_key:
                            await self._order_service.handle_inventory_reservation_failed(event)
                        elif message.routing_key == self._catalog_events_settings.release_failed_routing_key:
                            await self._order_service.handle_inventory_release_failed(event)
                    except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                        logger.warning(
                            "Discarding malformed catalog event: routing_key=%s",
                            message.routing_key,
                            exc_info=True,
                        )
            except Exception:
                logger.exception("Catalog event processing failed: routing_key=%s", message.routing_key)
                await self._session.rollback()
                raise

    async def start_consuming(self) -> None:
        logger.info("Starting order event consumers")
        channel = await self._rabbitmq.get_channel()
        await channel.set_qos(prefetch_count=1)
        payment_queue = await declare_order_payment_queue(
            channel,
            self._payment_events_settings,
        )
        await payment_queue.consume(
            callback=self._handle_payment_events
        )

        catalog_queue = await declare_order_catalog_queue(
            channel,
            self._catalog_events_settings,
        )
        await catalog_queue.consume(callback=self._handle_catalog_events)
        logger.info("Order event consumers started")
