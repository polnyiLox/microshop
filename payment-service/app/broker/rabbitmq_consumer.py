import json
import logging

from aio_pika.abc import AbstractIncomingMessage
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import PaymentCommandsExchangeSettings
from app.schemas import PaymentCreate
from app.services import PaymentService

from .rabbitmq_exchanges import declare_payment_commands_queue
from .rabbitmq import RabbitMQClient


logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    """Execute serialized payment commands before acknowledging delivery."""

    def __init__(
            self,
            rabbitmq: RabbitMQClient,
            payment_service: PaymentService,
            commands_settings: PaymentCommandsExchangeSettings,
            session: AsyncSession,
    ) -> None:
        self._rabbitmq = rabbitmq
        self._payment_service = payment_service
        self._commands_settings = commands_settings
        self._session = session

    async def _handle_payment_commands(
        self,
        message: AbstractIncomingMessage,
    ) -> None:
        try:
            async with message.process(requeue=True):
                try:
                    event = json.loads(message.body.decode("utf-8"))
                    logger.debug(
                        "Processing payment command: routing_key=%s, order_id=%s",
                        message.routing_key,
                        event.get("order_id"),
                    )

                    if message.routing_key == self._commands_settings.create_routing_key:
                        await self._payment_service.create_payment(
                            payment_data=PaymentCreate(
                                user_id=event["user_id"],
                                order_id=event["order_id"],
                                amount=event["amount"],
                            )
                        )
                    elif message.routing_key == self._commands_settings.cancel_routing_key:
                        await self._payment_service.cancel_pending_payments(event["order_id"])
                    elif message.routing_key == self._commands_settings.refund_routing_key:
                        await self._payment_service.refund_payment(event["order_id"])
                    else:
                        logger.warning(
                            "Unsupported payment command: routing_key=%s",
                            message.routing_key,
                        )
                    logger.debug(
                        "Payment command processed: routing_key=%s, order_id=%s",
                        message.routing_key,
                        event.get("order_id"),
                    )
                except (json.JSONDecodeError, UnicodeDecodeError, KeyError, ValidationError):
                    logger.warning(
                        "Discarding malformed payment command: routing_key=%s",
                        message.routing_key,
                        exc_info=True,
                    )
        except Exception:
            logger.exception(
                "Payment command failed: routing_key=%s",
                message.routing_key,
            )
            await self._session.rollback()
            raise

    async def start_consuming(self) -> None:
        logger.info("Starting payment command consumer")
        channel = await self._rabbitmq.get_channel()
        await channel.set_qos(prefetch_count=1)
        commands_queue = await declare_payment_commands_queue(
            channel,
            self._commands_settings,
        )
        await commands_queue.consume(callback=self._handle_payment_commands)
        logger.info("Payment command consumer started")
