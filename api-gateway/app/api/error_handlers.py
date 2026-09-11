from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.exceptions import ServiceTimeoutError, ServiceUnavailableError


async def service_unavailable_handler(
    request: Request,
    error: ServiceUnavailableError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Microservice is unavailable"},
    )


async def service_timeout_handler(
    request: Request,
    error: ServiceTimeoutError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={"detail": "Microservice response timeout"},
    )

