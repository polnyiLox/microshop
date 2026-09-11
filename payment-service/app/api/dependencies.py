from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import RedisCache
from app.broker import (
    KafkaClient,
    KafkaProducer,
    RabbitMQClient,
    RabbitMQPublisher,
)
from app.core.config import settings
from app.clients import BalanceClient
from app.db.session import get_session
from app.repositories import PaymentRepository
from app.services import PaymentService


rabbitmq_client = RabbitMQClient(settings=settings.rabbitmq)
rabbitmq_publisher = RabbitMQPublisher(
    rabbitmq=rabbitmq_client,
    exchange_settings=settings.payment_events_ex,
)
kafka_client = KafkaClient(settings.kafka)
kafka_producer = KafkaProducer(
    kafka=kafka_client,
    topics=settings.analytics_topics,
)
balance_client = BalanceClient(
    base_url=settings.auth_client.base_url,
    internal_token=settings.auth_client.internal_token,
)
redis_cache = RedisCache(settings.redis)


async def get_current_user_id(
    x_user_id: str = Header(alias="X-User-ID"),
) -> str:
    return x_user_id


def build_payment_service(session: AsyncSession) -> PaymentService:
    return PaymentService(
        payment_repo=PaymentRepository(session),
        session=session,
        publisher=rabbitmq_publisher,
        kafka_producer=kafka_producer,
        balance_client=balance_client,
        settings=settings.payment_events_ex,
        redis_cache=redis_cache,
        cache_ttl_seconds=settings.redis.ttl_seconds,
    )


async def get_payment_service(
    session: AsyncSession = Depends(get_session),
) -> PaymentService:
    return build_payment_service(session)
