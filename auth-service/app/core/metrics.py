from time import perf_counter
from typing import Callable, Awaitable

from fastapi import Request, Response, APIRouter
from fastapi.responses import Response as FastAPIResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

HTTP_REQUEST = Counter(
    "auth_http_requests_total",
    "Total number of HTTP requests handled by auth-service",
    ["method", "path", "status"]
)

HTTP_REQUEST_DURATION = Histogram(
    "auth_http_requests_duration_seconds",
    "Duration of HTTP requests handled by auth-service",
    ["method", "path"]
)


async def record_http_metrics(
        request: Request,
        call_next: Callable[[Request], Awaitable[FastAPIResponse]]
) -> FastAPIResponse:
    start_time = perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        path = getattr(route, "path", "unmatched")
        if path != "/metrics":
            HTTP_REQUEST.labels(
                method=request.method,
                path=path,
                status=str(status_code),
            ).inc()
            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                path=path,
            ).observe(perf_counter() - start_time)


router = APIRouter(include_in_schema=False)


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Expose metrics in the Prometheus text format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
