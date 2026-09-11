import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routers import v1_router
from app.api.dependencies import (
    build_payment_service,
    kafka_client,
    rabbitmq_client,
    redis_cache,
)
from app.broker.rabbitmq_consumer import RabbitMQConsumer
from app.core.config import settings
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.metrics import record_prometheus_metrics, router as metrics_router
from app.db.session import SessionLocal, engine_dispose
from app.exceptions import AppError


configure_logging(settings.logging.level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Own broker connections and the payment-command consumer session."""
    logger.info("Starting payment service")
    await rabbitmq_client.connect()

    try:
        await redis_cache.connect()
        await kafka_client.connect()

        async with SessionLocal() as session:
            payment_service = build_payment_service(session)
            rabbitmq_consumer = RabbitMQConsumer(
                rabbitmq=rabbitmq_client,
                payment_service=payment_service,
                commands_settings=settings.payment_commands_ex,
                session=session,
            )
            await rabbitmq_consumer.start_consuming()
            logger.info("Payment service started")
            yield
    finally:
        logger.info("Stopping payment service")
        await kafka_client.close()
        await rabbitmq_client.close()
        await redis_cache.close()
        await engine_dispose()
        logger.info("Payment service stopped")


app = FastAPI(
    lifespan=lifespan
)
app.middleware("http")(record_prometheus_metrics)

app.include_router(health_router)
app.include_router(v1_router)
app.include_router(metrics_router)

@app.exception_handler(AppError)
async def app_errors_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail
        }
    )
