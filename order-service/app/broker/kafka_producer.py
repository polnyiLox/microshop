import logging

from app.core.config import AnalyticsTopicsSettings
from app.schemas import OrderAnalyticsEvent

from .kafka_client import KafkaClient


logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(
            self,
            kafka_client: KafkaClient,
            topics: AnalyticsTopicsSettings
    ) -> None:
        self._kafka_client = kafka_client
        self._topics = topics

    async def publish(self, event: OrderAnalyticsEvent) -> None:
        logger.debug(
            "Publishing order analytics event: event_id=%s, event_type=%s",
            event.event_id,
            event.event_type,
        )
        producer = await self._kafka_client.get_producer()
        await producer.send_and_wait(
            topic=self._topics.order_events_topic,
            key=event.payload.order_id.encode("utf-8"),
            value=event.model_dump_json().encode("utf-8")
        )
        logger.debug("Order analytics event published: event_id=%s", event.event_id)
