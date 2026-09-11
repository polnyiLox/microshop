from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.broker import KafkaConsumer, KafkaClient
from app.cache import RedisCache
from app.core.config import settings
from app.db import mongodb_client
from app.repositories import AnalyticsEventRepository, AnalyticsRepository
from app.services import AnalyticsEventsService, AnalyticsService


redis_cache = RedisCache(settings.redis)


def get_database() -> AsyncDatabase:
    return mongodb_client.database


def get_analytics_service(
    database: AsyncDatabase = Depends(get_database),
) -> AnalyticsService:
    return AnalyticsService(
        repository=AnalyticsRepository(database),
        redis_cache=redis_cache,
        cache_ttl_seconds=settings.redis.ttl_seconds,
    )


kafka_client = KafkaClient(
    kafka_settings=settings.kafka,
    topics_settings=settings.analytics_topics,
)


def build_kafka_consumer(database: AsyncDatabase) -> KafkaConsumer:
    repository = AnalyticsEventRepository(database)
    service = AnalyticsEventsService(
        repository=repository,
        redis_cache=redis_cache,
    )
    return KafkaConsumer(
        kafka_client=kafka_client,
        analytics_service=service
    )
