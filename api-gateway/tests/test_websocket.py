from app.api.routers.v1.notification import get_websocket_access_token
from app.websocket.notification import build_notification_websocket_url


def test_extract_websocket_token_from_subprotocols() -> None:
    token = get_websocket_access_token(["bearer", "access-token"])

    assert token == "access-token"


def test_reject_websocket_token_without_bearer_subprotocol() -> None:
    token = get_websocket_access_token(["access-token"])

    assert token is None


def test_build_notification_websocket_url() -> None:
    url = build_notification_websocket_url(
        service_url="http://notification-service:8000/",
        user_id="user-id",
    )

    assert url == "ws://notification-service:8000/v1/notifications/ws/user-id"


def test_build_secure_notification_websocket_url() -> None:
    url = build_notification_websocket_url(
        service_url="https://notification.example.com",
        user_id="user-id",
    )

    assert url == "wss://notification.example.com/v1/notifications/ws/user-id"
