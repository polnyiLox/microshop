import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import RedisSettings

from .base import Cache


logger = logging.getLogger(__name__)


class RedisCache(Cache):

    def __init__(self, settings: RedisSettings) -> None:
        self._settings = settings
        self._client: Redis | None = None

    async def connect(self) -> None:
        if self._client is not None:
            return

        client = Redis.from_url(
            self._settings.url,
            decode_responses=True,
        )

        try:
            await client.ping()
        except (RedisError, OSError):
            await client.aclose()
            logger.warning(
                "Redis unavailable; notification-service will use PostgreSQL",
                exc_info=True,
            )
        else:
            self._client = client
            logger.info("Notification-service connected to Redis")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Notification-service Redis connection closed")

    async def get(self, key: str) -> str | None:
        if self._client is None:
            return None
        try:
            return await self._client.get(self._key(key))
        except (RedisError, OSError):
            logger.warning("Failed to get data from Redis", exc_info=True)
            return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if self._client is None:
            return
        try:
            await self._client.set(self._key(key), value, ex=ttl_seconds)
        except (RedisError, OSError):
            logger.warning("Failed to set data in Redis", exc_info=True)

    async def delete(self, *keys: str) -> None:
        if self._client is None:
            return
        try:
            await self._client.delete(*(self._key(key) for key in keys))
        except (RedisError, OSError):
            logger.warning("Failed to delete data from Redis", exc_info=True)

    def _key(self, key: str) -> str:
        return f"{self._settings.key_prefix}:{key}"

    def create_user_notifications_key(self, user_id: str) -> str:
        return f"{self._settings.user_notifications_key}{user_id}"
