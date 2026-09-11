import logging

import httpx
from fastapi import Request, Response

from app.exceptions import ServiceTimeoutError, ServiceUnavailableError


logger = logging.getLogger(__name__)


REQUEST_HEADERS_TO_REMOVE = {
    "connection",
    "content-length",
    "host",
    "transfer-encoding",
    "x-user-id",
    "x-user-role",
}

RESPONSE_HEADERS_TO_REMOVE = {
    "connection",
    "content-encoding",
    "content-length",
    "set-cookie",
    "transfer-encoding",
}


class ServiceClient:
    """Forward HTTP traffic while enforcing the gateway trust boundary."""

    def __init__(self, timeout_seconds: float) -> None:
        self._timeout_seconds = timeout_seconds

    async def forward(
        self,
        request: Request,
        service_url: str,
        user_id: str | None = None,
        user_role: str | None = None,
    ) -> Response:
        logger.debug(
            "Forwarding request: method=%s, path=%s, service=%s",
            request.method,
            request.url.path,
            service_url,
        )
        target_url = self._build_target_url(request, service_url)
        request_headers = self._prepare_request_headers(
            request,
            user_id=user_id,
            user_role=user_role,
        )
        request_body = await request.body()

        try:
            async with httpx.AsyncClient() as client:
                service_response = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=request_headers,
                    content=request_body,
                    timeout=self._timeout_seconds,
                    follow_redirects=False,
                )
        except httpx.TimeoutException:
            logger.warning(
                "Upstream request timed out: method=%s, path=%s, service=%s",
                request.method,
                request.url.path,
                service_url,
            )
            raise ServiceTimeoutError() from None
        except httpx.RequestError as exc:
            logger.error(
                "Upstream service unavailable: method=%s, path=%s, service=%s, error=%s",
                request.method,
                request.url.path,
                service_url,
                exc,
            )
            raise ServiceUnavailableError() from None

        logger.debug(
            "Upstream request completed: method=%s, path=%s, status_code=%d",
            request.method,
            request.url.path,
            service_response.status_code,
        )
        return self._build_gateway_response(service_response)

    def _build_target_url(self, request: Request, service_url: str) -> str:
        target_url = f"{service_url.rstrip('/')}{request.url.path}"

        if request.url.query:
            target_url = f"{target_url}?{request.url.query}"

        return target_url

    def _prepare_request_headers(
        self,
        request: Request,
        user_id: str | None = None,
        user_role: str | None = None,
    ) -> dict[str, str]:
        """Replace caller-supplied identity headers with verified JWT claims."""
        headers = dict(request.headers)

        for header_name in REQUEST_HEADERS_TO_REMOVE:
            headers.pop(header_name, None)

        if user_id is not None:
            headers["x-user-id"] = user_id
        if user_role is not None:
            headers["x-user-role"] = user_role

        return headers

    def _build_gateway_response(self, service_response: httpx.Response) -> Response:
        response_headers = {}

        for header_name, header_value in service_response.headers.items():
            if header_name.lower() not in RESPONSE_HEADERS_TO_REMOVE:
                response_headers[header_name] = header_value

        gateway_response = Response(
            content=service_response.content,
            status_code=service_response.status_code,
            headers=response_headers,
        )

        for cookie in service_response.headers.get_list("set-cookie"):
            gateway_response.headers.append("set-cookie", cookie)

        return gateway_response
