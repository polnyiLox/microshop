from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import service_timeout_handler, service_unavailable_handler
from app.api.routers import v1_router
from app.core.config import settings
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.metrics import record_http_metrics, router as metrics_router
from app.exceptions import ServiceTimeoutError, ServiceUnavailableError


configure_logging(settings.logging.level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("API Gateway started")
    try:
        yield
    finally:
        logger.info("API Gateway stopped")


app = FastAPI(
    title="API Gateway",
    version="0.1.0",
    lifespan=lifespan,
)
app.middleware("http")(record_http_metrics)

app.include_router(v1_router)
app.include_router(health_router)
app.include_router(metrics_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.middleware.allow_origins,
    allow_methods=settings.middleware.allow_methods,
    allow_headers=settings.middleware.allow_headers,
    allow_credentials=settings.middleware.allow_credentials,
)

app.add_exception_handler(
    ServiceUnavailableError,
    service_unavailable_handler,
)
app.add_exception_handler(
    ServiceTimeoutError,
    service_timeout_handler,
)
