from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import RedisCache
from app.clients import CatalogClient
from app.broker import RabbitMQClient, RabbitMQPublisher, KafkaClient, KafkaProducer
from app.core.config import settings
from app.db.session import get_session
from app.repositories import OrderRepository, OrderItemRepository
from app.services.order import OrderService


rabbitmq_client = RabbitMQClient(settings=settings.rabbitmq)
rabbitmq_publisher = RabbitMQPublisher(rabbitmq=rabbitmq_client)

kafka_client = KafkaClient(
    kafka_settings=settings.kafka,
)
kafka_producer = KafkaProducer(
    kafka_client=kafka_client,
    topics=settings.analytics_topics
)

async def get_current_user_id(
    x_user_id: str = Header(alias="X-User-ID"),
) -> str:
    return x_user_id


redis_cache = RedisCache(settings=settings.redis)


def build_order_service(
    session: AsyncSession,
    catalog_client: CatalogClient,
) -> OrderService:
    return OrderService(
        session=session,
        order_repo=OrderRepository(session=session),
        order_item_repo=OrderItemRepository(session=session),
        catalog_client=catalog_client,
        publisher=rabbitmq_publisher,
        order_events_settings=settings.order_events_ex,
        catalog_commands_settings=settings.catalog_commands_ex,
        payment_commands_settings=settings.payment_commands_ex,
        kafka_producer=kafka_producer,
        redis_cache=redis_cache,
        settings=settings
    )


async def get_catalog_client() -> CatalogClient:
    return CatalogClient(
        base_url=settings.catalog_client.base_url
    )


async def get_order_service(
        catalog_client: CatalogClient = Depends(get_catalog_client),
        session: AsyncSession = Depends(get_session)
) -> OrderService:
    return build_order_service(session=session, catalog_client=catalog_client)
