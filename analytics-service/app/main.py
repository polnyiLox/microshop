import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import build_kafka_consumer, kafka_client, redis_cache
from app.api.routers import v1_router
from app.core.config import settings
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.metrics import record_http_metrics, router as metrics_router
from app.db import mongodb_client
from app.db.indexes import create_indexes
from app.exceptions import AppError


configure_logging(settings.logging.level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize MongoDB indexes and own the background Kafka task."""
    logger.info("Starting analytics service")
    await mongodb_client.connect()
    try:
        await redis_cache.connect()
        await kafka_client.connect()

        database = mongodb_client.database
        await create_indexes(database)
        kafka_consumer = build_kafka_consumer(database)
        consumer_task = asyncio.create_task(
            kafka_consumer.start_consuming()
        )

        try:
            logger.info("Analytics service started")
            yield
        finally:
            consumer_task.cancel()
            with suppress(asyncio.CancelledError):
                await consumer_task
    finally:
        logger.info("Stopping analytics service")
        await kafka_client.close()
        await redis_cache.close()
        await mongodb_client.close()
        logger.info("Analytics service stopped")


app = FastAPI(lifespan=lifespan)
app.middleware("http")(record_http_metrics)

app.include_router(v1_router)
app.include_router(health_router)
app.include_router(metrics_router)

@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
