from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import APIRouter, Request, Response
from fastapi.responses import Response as FastAPIResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


HTTP_REQUESTS = Counter(
    "catalog_http_requests_total",
    "Total number of HTTP requests handled by catalog-service.",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "catalog_http_request_duration_seconds",
    "Catalog-service HTTP request duration in seconds.",
    ["method", "path"],
)


async def record_http_metrics(
    request: Request,
    call_next: Callable[[Request], Awaitable[FastAPIResponse]],
) -> FastAPIResponse:
    """Record request count and latency using route templates as labels."""
    started_at = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        path = getattr(route, "path", "unmatched")
        if path != "/metrics":
            HTTP_REQUESTS.labels(
                method=request.method,
                path=path,
                status=str(status_code),
            ).inc()
            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                path=path,
            ).observe(perf_counter() - started_at)


router = APIRouter(include_in_schema=False)


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Expose metrics in the Prometheus text format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
