from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response as StarletteResponse


HTTP_REQUESTS = Counter(
    "notification_http_requests_total",
    "Total HTTP requests handled by notification-service.",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "notification_http_request_duration_seconds",
    "Notification-service HTTP request duration in seconds.",
    ["method", "path"],
)


async def record_http_metrics(
    request: Request,
    call_next: Callable[[Request], Awaitable[StarletteResponse]],
) -> StarletteResponse:
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
            HTTP_REQUESTS.labels(request.method, path, str(status_code)).inc()
            HTTP_REQUEST_DURATION.labels(request.method, path).observe(
                perf_counter() - started_at,
            )


router = APIRouter(include_in_schema=False)


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
