from app.clients import ServiceClient
from app.core.config import settings


def get_service_client() -> ServiceClient:
    return ServiceClient(
        timeout_seconds=settings.http_client.timeout_seconds,
    )

