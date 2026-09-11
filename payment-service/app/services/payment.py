import asyncio
import json
from json import JSONDecodeError
import logging
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.broker import KafkaProducer, RabbitMQPublisher
from app.cache import RedisCache
from app.clients import BalanceClient
from app.core.config import PaymentEventsExchangeSettings
from app.db.models import Payment
from app.enums import PaymentAnalyticsEventTypeEnum, PaymentStatusEnum
from app.exceptions import (
    InvalidPaymentStatusTransitionError,
    InsufficientBalanceError,
    PaymentNotFoundError,
)
from app.repositories import PaymentRepository
from app.schemas import (
    PaymentAnalyticsEvent,
    PaymentAnalyticsEventPayload,
    PaymentCreate,
    PaymentRead,
    PaymentStatusUpdate,
)


logger = logging.getLogger(__name__)


class PaymentService:
    """Coordinate payment state transitions with broker notifications."""

    def __init__(
        self,
        payment_repo: PaymentRepository,
        session: AsyncSession,
        publisher: RabbitMQPublisher,
        kafka_producer: KafkaProducer,
        balance_client: BalanceClient,
        settings: PaymentEventsExchangeSettings,
        redis_cache: RedisCache,
        cache_ttl_seconds: int,
    ) -> None:
        self._payment_repo = payment_repo
        self._session = session
        self._publisher = publisher
        self._kafka_producer = kafka_producer
        self._balance_client = balance_client
        self._settings = settings
        self._redis_cache = redis_cache
        self._cache_ttl_seconds = cache_ttl_seconds

    async def _invalidate_payment(self, payment: Payment) -> None:
        logger.debug("Invalidating payment cache: payment_id=%s", payment.id)
        await self._redis_cache.delete(
            self._redis_cache.create_payment_key(payment.id),
            self._redis_cache.create_order_payments_key(payment.order_id),
            self._redis_cache.create_user_payments_key(payment.user_id),
        )

    async def _get_existing_payment(self, payment_id: str) -> Payment:
        payment = await self._payment_repo.get_by_id(payment_id)
        if payment is None:
            logger.warning("Payment not found: payment_id=%s", payment_id)
            raise PaymentNotFoundError()
        return payment

    async def _publish_payment_event(
        self,
        payment: PaymentRead,
        routing_key: str,
        event_type: PaymentAnalyticsEventTypeEnum,
    ) -> None:
        logger.debug(
            "Publishing payment event: payment_id=%s, routing_key=%s, event_type=%s",
            payment.id,
            routing_key,
            event_type,
        )
        rabbitmq_event = {
            "event_id": str(uuid4()),
            "user_id": payment.user_id,
            "order_id": payment.order_id,
            "status": payment.status,
            "amount": payment.amount,
        }
        await self._publisher.publish(
            routing_key=routing_key,
            payload=rabbitmq_event,
        )
        await self._kafka_producer.publish(
            PaymentAnalyticsEvent(
                event_type=event_type,
                payload=PaymentAnalyticsEventPayload(
                    payment_id=payment.id,
                    order_id=payment.order_id,
                    user_id=payment.user_id,
                    amount=payment.amount,
                    status=payment.status,
                ),
            )
        )
        logger.debug("Payment event published: payment_id=%s", payment.id)

    async def create_payment(self, payment_data: PaymentCreate) -> PaymentRead:
        logger.info(
            "Creating payment: order_id=%s, user_id=%s, amount=%d",
            payment_data.order_id,
            payment_data.user_id,
            payment_data.amount,
        )
        active_payment = await self._payment_repo.get_by_order_id_for_statuses(
            order_id=payment_data.order_id,
            statuses={
                PaymentStatusEnum.PENDING,
                PaymentStatusEnum.PROCESSING,
                PaymentStatusEnum.SUCCEEDED,
            },
        )
        if active_payment is not None:
            logger.warning(
                "Active payment already exists: order_id=%s, payment_id=%s",
                payment_data.order_id,
                active_payment.id,
            )
            return PaymentRead.model_validate(active_payment)

        payment = await self._payment_repo.create(
            order_id=payment_data.order_id,
            amount=payment_data.amount,
            user_id=payment_data.user_id
        )
        await self._session.commit()

        logger.debug("Invalidating payment list caches: payment_id=%s", payment.id)
        await self._redis_cache.delete(
            self._redis_cache.create_order_payments_key(payment.order_id),
            self._redis_cache.create_user_payments_key(payment.user_id),
        )
        created_payment = PaymentRead.model_validate(payment)
        await self._publish_payment_event(
            created_payment,
            self._settings.payment_created_routing_key,
            PaymentAnalyticsEventTypeEnum.CREATED,
        )
        logger.info(
            "Payment created: payment_id=%s, order_id=%s",
            payment.id,
            payment.order_id,
        )
        return created_payment

    async def get_payment_by_id(self, payment_id: str) -> PaymentRead:
        logger.debug("Getting payment: payment_id=%s", payment_id)
        cache_key = self._redis_cache.create_payment_key(payment_id)
        cached_payment = await self._redis_cache.get(cache_key)
        if cached_payment is not None:
            logger.debug("Payment cache hit: payment_id=%s", payment_id)
            try:
                return PaymentRead.model_validate_json(cached_payment)
            except ValidationError:
                logger.warning("Invalid payment found in cache: payment_id=%s", payment_id)
                await self._redis_cache.delete(cache_key)
        else:
            logger.debug("Payment cache miss: payment_id=%s", payment_id)

        payment = await self._get_existing_payment(payment_id)
        result = PaymentRead.model_validate(payment)
        await self._redis_cache.set(
            cache_key,
            result.model_dump_json(),
            self._cache_ttl_seconds,
        )
        return result

    async def get_payments_by_order_id(self, order_id: str) -> list[PaymentRead]:
        logger.debug("Getting payments for order: order_id=%s", order_id)
        cache_key = self._redis_cache.create_order_payments_key(order_id)
        cached_payments = await self._redis_cache.get(cache_key)
        if cached_payments is not None:
            logger.debug("Order payments cache hit: order_id=%s", order_id)
            try:
                values = json.loads(cached_payments)
                return [PaymentRead.model_validate(value) for value in values]
            except (JSONDecodeError, ValidationError, TypeError):
                logger.warning("Invalid order payments found in cache: order_id=%s", order_id)
                await self._redis_cache.delete(cache_key)
        else:
            logger.debug("Order payments cache miss: order_id=%s", order_id)

        payments = await self._payment_repo.get_all_by_order_id(order_id)
        result = [PaymentRead.model_validate(payment) for payment in payments]
        await self._redis_cache.set(
            cache_key,
            json.dumps([payment.model_dump(mode="json") for payment in result]),
            self._cache_ttl_seconds,
        )
        logger.debug("Payments loaded for order: order_id=%s, count=%d", order_id, len(result))
        return result

    async def get_payments_by_user_id(self, user_id: str) -> list[PaymentRead]:
        logger.debug("Getting payments for user: user_id=%s", user_id)
        cache_key = self._redis_cache.create_user_payments_key(user_id)
        cached_payments = await self._redis_cache.get(cache_key)
        if cached_payments is not None:
            logger.debug("User payments cache hit: user_id=%s", user_id)
            try:
                values = json.loads(cached_payments)
                return [PaymentRead.model_validate(value) for value in values]
            except (JSONDecodeError, ValidationError, TypeError):
                logger.warning("Invalid user payments found in cache: user_id=%s", user_id)
                await self._redis_cache.delete(cache_key)
        else:
            logger.debug("User payments cache miss: user_id=%s", user_id)

        payments = await self._payment_repo.get_all_by_user_id(user_id)
        result = [PaymentRead.model_validate(payment) for payment in payments]
        await self._redis_cache.set(
            cache_key,
            json.dumps([payment.model_dump(mode="json") for payment in result]),
            self._cache_ttl_seconds,
        )
        logger.debug("Payments loaded for user: user_id=%s, count=%d", user_id, len(result))
        return result

    async def cancel_pending_payments(self, order_id: str) -> None:
        logger.info("Cancelling pending payments: order_id=%s", order_id)
        payments = [
            PaymentRead.model_validate(payment)
            for payment in await self._payment_repo.get_all_by_order_id(order_id)
        ]
        for payment in payments:
            if payment.status == PaymentStatusEnum.PENDING:
                await self.cancel_payment(payment.id)
        logger.info("Pending payment cancellation completed: order_id=%s", order_id)

    async def cancel_payment(self, payment_id: str) -> PaymentRead:
        logger.info("Cancelling payment: payment_id=%s", payment_id)
        payment = await self._get_existing_payment(payment_id)
        if payment.status == PaymentStatusEnum.CANCELLED:
            logger.debug("Payment is already cancelled: payment_id=%s", payment_id)
            return PaymentRead.model_validate(payment)
        return await self.update_payment_status(
            payment_id=payment.id,
            update_data=PaymentStatusUpdate(status=PaymentStatusEnum.CANCELLED),
        )

    async def refund_payment(self, order_id: str) -> PaymentRead:
        logger.info("Refunding payment: order_id=%s", order_id)
        payments = [
            PaymentRead.model_validate(payment)
            for payment in await self._payment_repo.get_all_by_order_id(order_id)
        ]
        for payment in payments:
            if payment.status == PaymentStatusEnum.REFUNDED:
                logger.debug("Payment is already refunded: payment_id=%s", payment.id)
                return payment
            if payment.status == PaymentStatusEnum.SUCCEEDED:
                logger.debug("Crediting user balance for refund: payment_id=%s", payment.id)
                await self._balance_client.credit(
                    user_id=payment.user_id,
                    amount=payment.amount,
                    reference=f"payment-refund:{payment.id}",
                )
                return await self.update_payment_status(
                    payment_id=payment.id,
                    update_data=PaymentStatusUpdate(
                        status=PaymentStatusEnum.REFUNDED,
                    ),
                )
        logger.warning("Refundable payment not found: order_id=%s", order_id)
        raise PaymentNotFoundError()

    async def update_payment_status(
        self,
        payment_id: str,
        update_data: PaymentStatusUpdate,
    ) -> PaymentRead:
        logger.info(
            "Updating payment status: payment_id=%s, target_status=%s",
            payment_id,
            update_data.status,
        )
        payment = await self._get_existing_payment(payment_id)
        if payment.status == update_data.status:
            logger.debug("Payment already has requested status: payment_id=%s", payment_id)
            return PaymentRead.model_validate(payment)
        if not payment.status.can_transition_to(update_data.status):
            logger.warning(
                "Invalid payment status transition: payment_id=%s, current=%s, target=%s",
                payment_id,
                payment.status,
                update_data.status,
            )
            raise InvalidPaymentStatusTransitionError(
                f"Cannot transition from {payment.status} to {update_data.status}"
            )

        payment = await self._payment_repo.update_status(payment, update_data.status)
        await self._session.commit()
        await self._invalidate_payment(payment)
        updated_payment = PaymentRead.model_validate(payment)
        events = {
            PaymentStatusEnum.SUCCEEDED: (
                self._settings.payment_succeeded_routing_key,
                PaymentAnalyticsEventTypeEnum.SUCCEEDED,
            ),
            PaymentStatusEnum.FAILED: (
                self._settings.payment_failed_routing_key,
                PaymentAnalyticsEventTypeEnum.FAILED,
            ),
            PaymentStatusEnum.CANCELLED: (
                self._settings.payment_cancelled_routing_key,
                PaymentAnalyticsEventTypeEnum.CANCELLED,
            ),
            PaymentStatusEnum.REFUNDED: (
                self._settings.payment_refunded_routing_key,
                PaymentAnalyticsEventTypeEnum.REFUNDED,
            ),
        }
        event_settings = events.get(updated_payment.status)
        if event_settings is not None:
            routing_key, event_type = event_settings
            await self._publish_payment_event(
                updated_payment,
                routing_key,
                event_type,
            )
        logger.info(
            "Payment status updated: payment_id=%s, status=%s",
            payment_id,
            updated_payment.status,
        )
        return updated_payment

    async def complete_payment(
        self,
        payment_id: str,
    ) -> PaymentRead:
        """Simulate provider processing and complete an eligible payment."""
        logger.info("Completing payment: payment_id=%s", payment_id)
        payment = await self._get_existing_payment(payment_id)

        if payment.status == PaymentStatusEnum.SUCCEEDED:
            logger.debug("Payment is already completed: payment_id=%s", payment_id)
            return PaymentRead.model_validate(payment)

        if payment.status == PaymentStatusEnum.PENDING:
            await self.update_payment_status(
                payment_id=payment.id,
                update_data=PaymentStatusUpdate(
                    status=PaymentStatusEnum.PROCESSING
                )
            )
        elif payment.status != PaymentStatusEnum.PROCESSING:
            logger.warning(
                "Payment cannot be completed from current status: payment_id=%s, status=%s",
                payment_id,
                payment.status,
            )
            raise InvalidPaymentStatusTransitionError(
                f"Cannot complete payment with status {payment.status}"
            )

        try:
            logger.debug("Debiting user balance: payment_id=%s", payment.id)
            await self._balance_client.debit(
                user_id=payment.user_id,
                amount=payment.amount,
                reference=f"payment:{payment.id}",
            )
        except InsufficientBalanceError:
            logger.warning("Insufficient balance for payment: payment_id=%s", payment.id)
            return await self.update_payment_status(
                payment_id=payment.id,
                update_data=PaymentStatusUpdate(status=PaymentStatusEnum.FAILED),
            )

        # Represents short processing latency of an external provider.
        await asyncio.sleep(1)

        completed_payment = await self.update_payment_status(
            payment_id=payment.id,
            update_data=PaymentStatusUpdate(
                status=PaymentStatusEnum.SUCCEEDED
            )
        )

        logger.info("Payment completed: payment_id=%s", payment_id)
        return completed_payment

    async def retry_payment(self, payment_id: str) -> PaymentRead:
        logger.info("Retrying payment: payment_id=%s", payment_id)
        failed_payment = await self._get_existing_payment(payment_id)
        if failed_payment.status != PaymentStatusEnum.FAILED:
            logger.warning(
                "Payment retry rejected: payment_id=%s, status=%s",
                payment_id,
                failed_payment.status,
            )
            raise InvalidPaymentStatusTransitionError(
                f"Cannot retry payment with status {failed_payment.status}",
            )

        new_payment = await self.create_payment(
            PaymentCreate(
                user_id=failed_payment.user_id,
                order_id=failed_payment.order_id,
                amount=failed_payment.amount,
            ),
        )
        result = await self.complete_payment(new_payment.id)
        logger.info(
            "Payment retry completed: previous_payment_id=%s, payment_id=%s",
            payment_id,
            result.id,
        )
        return result
