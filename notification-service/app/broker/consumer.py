import asyncio
import json
import logging

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import OrderEventsExchangeSettings, PaymentEventsExchangeSettings
from app.services import NotificationService

from .exchanges import declare_notification_order_queue, declare_notification_payment_queue
from .rabbitmq import RabbitMQClient


logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    """Persist user notifications before acknowledging broker events."""

    def __init__(
            self,
            rabbitmq: RabbitMQClient,
            order_events_exchange_settings: OrderEventsExchangeSettings,
            payment_events_exchange_settings: PaymentEventsExchangeSettings,
            notification_service: NotificationService,
            session: AsyncSession,
    ) -> None:
        self._rabbitmq = rabbitmq
        self._order_events_exchange_settings = order_events_exchange_settings
        self._payment_events_exchange_settings = payment_events_exchange_settings
        self._notification_service = notification_service
        self._session = session
        self._processing_lock = asyncio.Lock()

    async def _handle_order_events(self, message: AbstractIncomingMessage) -> None:
        async with self._processing_lock:
            try:
                async with message.process(requeue=True):
                    try:
                        event = json.loads(message.body.decode("utf-8"))
                        logger.debug(
                            "Received order event routing_key=%s",
                            message.routing_key,
                        )

                        if message.routing_key == self._order_events_exchange_settings.order_created_routing_key:
                            not_message = {
                                "event": "Order created",
                                "order_id": event["order_id"],
                            }
                        elif message.routing_key == self._order_events_exchange_settings.order_cancelled_routing_key:
                            not_message = {
                                "event": "Order canceled",
                                "order_id": event["order_id"],
                            }
                        else:
                            logger.warning(
                                "Skipping unsupported order event routing_key=%s",
                                message.routing_key,
                            )
                            return

                        await self._notification_service.create_notification(
                            user_id=event["user_id"],
                            message=not_message,
                        )
                    except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                        logger.warning(
                            "Discarding malformed order event: routing_key=%s",
                            message.routing_key,
                            exc_info=True,
                        )
            except Exception:
                logger.exception(
                    "Failed to handle order event routing_key=%s",
                    message.routing_key,
                )
                await self._session.rollback()
                raise

    async def _handle_payment_events(self, message: AbstractIncomingMessage) -> None:
        async with self._processing_lock:
            try:
                async with message.process(requeue=True):
                    try:
                        event = json.loads(message.body.decode("utf-8"))
                        logger.debug(
                            "Received payment event routing_key=%s",
                            message.routing_key,
                        )

                        if message.routing_key == self._payment_events_exchange_settings.payment_succeeded_routing_key:
                            not_message = {
                                "event": "Payment succeeded",
                                "order_id": event["order_id"],
                            }
                        elif message.routing_key == self._payment_events_exchange_settings.payment_failed_routing_key:
                            not_message = {
                                "event": "Payment failed",
                                "order_id": event["order_id"],
                            }
                        elif message.routing_key == self._payment_events_exchange_settings.payment_cancelled_routing_key:
                            not_message = {
                                "event": "Payment cancelled",
                                "order_id": event["order_id"],
                            }
                        elif message.routing_key == self._payment_events_exchange_settings.payment_refunded_routing_key:
                            not_message = {
                                "event": "Payment refunded success",
                                "order_id": event["order_id"],
                            }
                        else:
                            logger.warning(
                                "Skipping unsupported payment event routing_key=%s",
                                message.routing_key,
                            )
                            return

                        await self._notification_service.create_notification(
                            user_id=event["user_id"],
                            message=not_message,
                        )
                    except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
                        logger.warning(
                            "Discarding malformed payment event: routing_key=%s",
                            message.routing_key,
                            exc_info=True,
                        )
            except Exception:
                logger.exception(
                    "Failed to handle payment event routing_key=%s",
                    message.routing_key,
                )
                await self._session.rollback()
                raise

    async def start_consuming(self) -> None:
        logger.info("Starting notification RabbitMQ consumers")
        channel = await self._rabbitmq.get_channel()
        await channel.set_qos(prefetch_count=1)

        notification_order_queue = await declare_notification_order_queue(
            settings=self._order_events_exchange_settings,
            channel=channel,
        )
        notification_payment_queue = await declare_notification_payment_queue(
            settings=self._payment_events_exchange_settings,
            channel=channel,
        )

        await notification_order_queue.consume(
            callback=self._handle_order_events
        )
        await notification_payment_queue.consume(
            callback=self._handle_payment_events
        )
        logger.info("Notification RabbitMQ consumers started")
