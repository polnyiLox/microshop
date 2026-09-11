from time import perf_counter
from typing import Callable, Awaitable

from fastapi import Request, Response, APIRouter
from fastapi.responses import Response as FastAPIResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

HTTP_REQUESTS = Counter(
    "order_http_requests_total",
    "Total number of HTTP requests handled by order-service",
    ["method", "path", "status"]
)

HTTP_REQUESTS_DURATION = Histogram(
    "order_http_requests_duration_seconds",
    "Duration of HTTP requests handled by order-service",
    ["method", "path"]
)


async def record_prometheus_metrics(
        request: Request,
        call_next: Callable[[Request], Awaitable[FastAPIResponse]],
) -> FastAPIResponse:
    start = perf_counter()
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

            HTTP_REQUESTS_DURATION.labels(
                method=request.method,
                path=path,
            ).observe(perf_counter() - start)


router = APIRouter(include_in_schema=False)


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
