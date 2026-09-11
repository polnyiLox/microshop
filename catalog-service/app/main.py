from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routers import v1_router
from app.broker import RabbitMQClient, RabbitMQConsumer, RabbitMQPublisher
from app.cache import RedisCache
from app.core.config import settings
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.metrics import record_http_metrics, router as metrics_router
from app.core.s3_client import S3Client
from app.db.session import SessionLocal, engine_dispose
from app.exceptions import AppError
from app.repositories import ProductRepository
from app.services import InventoryService, ProductService


configure_logging(settings.logging.level)
logger = logging.getLogger(__name__)

rabbitmq_client = RabbitMQClient(settings.rabbitmq)
redis_cache = RedisCache(settings.redis)
s3_client = S3Client(settings.s3)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Keep external connections and the command consumer alive with the API."""
    logger.info("Starting catalog service")
    await redis_cache.connect()
    await s3_client.ensure_bucket()
    app.state.cache = redis_cache
    app.state.s3_client = s3_client
    try:
        await rabbitmq_client.connect()
        async with SessionLocal() as session:
            product_service = ProductService(
                ProductRepository(session),
                session,
                redis_cache,
                settings.redis.ttl_seconds,
                s3_client,
                settings.s3,
            )
            publisher = RabbitMQPublisher(
                rabbitmq_client,
                settings.catalog_events_ex,
            )
            consumer = RabbitMQConsumer(
                rabbitmq_client,
                InventoryService(
                    product_service,
                    publisher,
                    settings.catalog_events_ex,
                ),
                settings.catalog_commands_ex,
                session,
            )
            await consumer.start_consuming()
            logger.info("Catalog service started")
            yield
    finally:
        logger.info("Stopping catalog service")
        await rabbitmq_client.close()
        await redis_cache.close()
        await engine_dispose()
        logger.info("Catalog service stopped")


app = FastAPI(lifespan=lifespan)
app.middleware("http")(record_http_metrics)

app.include_router(v1_router)
app.include_router(health_router)
app.include_router(metrics_router)

@app.exception_handler(AppError)
async def app_errors_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail
        }
    )
