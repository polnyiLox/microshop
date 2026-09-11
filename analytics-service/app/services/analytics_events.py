import logging

from pymongo.errors import DuplicateKeyError

from app.cache import RedisCache
from app.repositories import AnalyticsEventRepository
from app.schemas import AnalyticsEventSchema


logger = logging.getLogger(__name__)


class AnalyticsEventsService:
    """Store analytics events idempotently by their unique event identifier."""

    def __init__(
        self,
        repository: AnalyticsEventRepository,
        redis_cache: RedisCache,
    ) -> None:
        self._repository = repository
        self._redis_cache = redis_cache

    async def process(self, event: AnalyticsEventSchema) -> None:
        """Treat a duplicate delivery as successfully processed."""
        logger.debug(
            "Processing analytics event: event_id=%s, event_type=%s",
            event.event_id,
            event.event_type,
        )
        try:
            await self._repository.create(event)
        except DuplicateKeyError:
            logger.debug(
                "Skipping duplicate analytics event: event_id=%s",
                event.event_id,
            )
            return
        await self._redis_cache.delete(
            self._redis_cache.create_overview_key()
        )
        logger.info(
            "Analytics event stored: event_id=%s, event_type=%s",
            event.event_id,
            event.event_type,
        )
