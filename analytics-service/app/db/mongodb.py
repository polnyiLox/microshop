import logging

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import MongoDBSettings, settings


logger = logging.getLogger(__name__)


class MongoDBClient:
    def __init__(self, mongodb_settings: MongoDBSettings) -> None:
        self._settings = mongodb_settings
        self._client: AsyncMongoClient | None = None
        self._database: AsyncDatabase | None = None

    @property
    def database(self) -> AsyncDatabase:
        if self._database is None:
            raise RuntimeError("MongoDB client is not connected")
        return self._database

    async def connect(self) -> None:
        if self._client is not None:
            logger.debug("MongoDB client is already connected")
            return

        logger.info("Connecting analytics-service to MongoDB")
        client = AsyncMongoClient(self._settings.url)
        try:
            await client.admin.command("ping")
        except Exception:
            logger.exception("Failed to connect analytics-service to MongoDB")
            await client.close()
            raise

        self._client = client
        self._database = client[self._settings.name]
        logger.info("Analytics-service connected to MongoDB")

    async def close(self) -> None:
        if self._client is not None:
            logger.info("Closing analytics-service MongoDB connection")
            await self._client.close()
            logger.info("Analytics-service MongoDB connection closed")

        self._client = None
        self._database = None


mongodb_client = MongoDBClient(settings.mongodb)
