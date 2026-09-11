from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import build_notification_service, redis_cache
from app.api.routers import v1_router
from app.broker import RabbitMQClient, RabbitMQConsumer
from app.core.config import settings
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.metrics import record_http_metrics, router as metrics_router
from app.db.session import SessionLocal, engine_dispose
from app.exceptions import AppError


configure_logging(settings.logging.level)
logger = logging.getLogger(__name__)

rabbitmq_client = RabbitMQClient(settings.rabbitmq)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Own the broker consumer session and release all external resources."""
    logger.info("Starting notification service")
    await rabbitmq_client.connect()

    try:
        await redis_cache.connect()
        async with SessionLocal() as session:
            consumer = RabbitMQConsumer(
                rabbitmq=rabbitmq_client,
                order_events_exchange_settings=settings.order_events_ex,
                payment_events_exchange_settings=settings.payment_events_ex,
                notification_service=build_notification_service(session),
                session=session,
            )
            try:
                await consumer.start_consuming()
                logger.info("Notification service started")
                yield
            finally:
                await rabbitmq_client.close()
    finally:
        logger.info("Stopping notification service")
        await redis_cache.close()
        await engine_dispose()
        logger.info("Notification service stopped")


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
