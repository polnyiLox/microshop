import asyncio
import json
import logging

from pydantic import ValidationError

from app.broker.kafka_client import KafkaClient
from app.schemas import AnalyticsEventSchema
from app.services import AnalyticsEventsService


logger = logging.getLogger(__name__)
RETRY_DELAY_SECONDS = 1


class KafkaConsumer:
    """Persist valid events before committing their Kafka offsets."""

    def __init__(
            self,
            kafka_client: KafkaClient,
            analytics_service: AnalyticsEventsService
    ) -> None:
        self._kafka_client = kafka_client
        self._analytics_service = analytics_service

    async def start_consuming(self) -> None:
        consumer = await self._kafka_client.get_consumer()

        async for message in consumer:
            try:
                event_data = json.loads(message.value)
                event = AnalyticsEventSchema.model_validate(event_data)
            except (json.JSONDecodeError, ValidationError):
                logger.warning(
                    "Skipping invalid Kafka message from %s partition %s offset %s",
                    message.topic,
                    message.partition,
                    message.offset,
                )
                await consumer.commit()
                continue

            while True:
                try:
                    logger.debug(
                        "Processing Kafka message: topic=%s, partition=%s, offset=%s",
                        message.topic,
                        message.partition,
                        message.offset,
                    )
                    await self._analytics_service.process(event)
                    break
                except Exception:
                    # Do not commit the offset until MongoDB accepts the event.
                    logger.exception(
                        "Failed to save analytics event %s. Retrying",
                        event.event_id,
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)

            await consumer.commit()
            logger.debug(
                "Kafka offset committed: topic=%s, partition=%s, offset=%s",
                message.topic,
                message.partition,
                message.offset,
            )
