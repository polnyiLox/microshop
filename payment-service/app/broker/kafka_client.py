import logging

from aiokafka import AIOKafkaProducer

from app.core.config import KafkaSettings


logger = logging.getLogger(__name__)


class KafkaClient:
    def __init__(self, settings: KafkaSettings) -> None:
        self._settings = settings
        self._producer: AIOKafkaProducer | None = None

    async def connect(self) -> None:
        if self._producer is not None:
            logger.debug("Kafka producer is already connected")
            return

        logger.info("Connecting payment-service producer to Kafka")
        producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.bootstrap_servers,
            client_id=self._settings.client_id,
            acks=self._settings.acks,
        )
        await producer.start()
        self._producer = producer
        logger.info("Payment-service Kafka producer connected")

    async def get_producer(self) -> AIOKafkaProducer:
        await self.connect()
        assert self._producer is not None
        return self._producer

    async def close(self) -> None:
        if self._producer is not None:
            logger.info("Closing payment-service Kafka producer")
            await self._producer.stop()
            logger.info("Payment-service Kafka producer closed")

        self._producer = None
