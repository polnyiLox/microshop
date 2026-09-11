import logging

from aiokafka import AIOKafkaConsumer

from app.core.config import KafkaSettings, AnalyticsTopicsSettings


logger = logging.getLogger(__name__)


class KafkaClient:
    def __init__(
            self,
            kafka_settings: KafkaSettings,
            topics_settings: AnalyticsTopicsSettings
    ):
        self._kafka_settings = kafka_settings
        self._topics_settings = topics_settings
        self._consumer: AIOKafkaConsumer | None = None

    async def connect(self) -> None:
        if self._consumer is not None:
            logger.debug("Kafka consumer is already connected")
            return

        logger.info("Connecting analytics consumer to Kafka")
        consumer = AIOKafkaConsumer(
            self._topics_settings.order_events_topic,
            self._topics_settings.payment_events_topic,
            bootstrap_servers=self._kafka_settings.bootstrap_servers,
            client_id=self._kafka_settings.client_id,
            group_id=self._kafka_settings.group_id,
            auto_offset_reset=self._kafka_settings.auto_offset_reset,
            enable_auto_commit=self._kafka_settings.enable_auto_commit,
        )

        await consumer.start()
        self._consumer = consumer
        logger.info("Analytics Kafka consumer connected")

    async def get_consumer(self) -> AIOKafkaConsumer:
        await self.connect()
        assert self._consumer is not None
        return self._consumer

    async def close(self) -> None:
        if self._consumer is not None:
            logger.info("Closing analytics Kafka consumer")
            await self._consumer.stop()
            logger.info("Analytics Kafka consumer closed")

        self._consumer = None
