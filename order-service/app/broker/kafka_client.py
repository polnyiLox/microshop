import logging

from aiokafka import AIOKafkaProducer

from app.core.config import KafkaSettings


logger = logging.getLogger(__name__)


class KafkaClient:
    def __init__(self, kafka_settings: KafkaSettings):
        self._kafka_settings = kafka_settings
        self._producer: AIOKafkaProducer | None = None

    async def connect(self) -> None:
        if self._producer is not None:
            logger.debug("Kafka producer is already connected")
            return

        logger.info("Connecting order-service producer to Kafka")
        producer: AIOKafkaProducer = AIOKafkaProducer(
            bootstrap_servers=self._kafka_settings.bootstrap_servers,
            client_id=self._kafka_settings.client_id,
            acks=self._kafka_settings.acks
        )

        await producer.start()
        self._producer: AIOKafkaProducer = producer
        logger.info("Order-service Kafka producer connected")

    async def get_producer(self) -> AIOKafkaProducer:
        await self.connect()
        assert self._producer is not None
        return self._producer

    async def close(self) -> None:
        if self._producer is not None:
            logger.info("Closing order-service Kafka producer")
            await self._producer.stop()
            logger.info("Order-service Kafka producer closed")

        self._producer = None
