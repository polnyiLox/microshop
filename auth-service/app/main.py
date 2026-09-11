from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.dependencies import redis_cache
from app.api.routers import v1_router
from app.core.config import settings
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.metrics import record_http_metrics, router as metrics_router
from app.db.session import engine_dispose
from app.exceptions import AppError


configure_logging(settings.logging.level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting auth service")
    await redis_cache.connect()
    try:
        logger.info("Auth service started")
        yield
    finally:
        logger.info("Stopping auth service")
        await redis_cache.close()
        await engine_dispose()
        logger.info("Auth service stopped")


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
