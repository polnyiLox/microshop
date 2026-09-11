from fastapi import Response
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_service_client
from app.core.config import settings
from app.main import app
from app.schemas import CurrentUser


class FakeServiceClient:
    async def forward(self, request, service_url: str, **kwargs) -> Response:
        return Response(
            content=b'{"service_url":"' + service_url.encode() + b'"}',
            media_type="application/json",
        )


def override_current_user() -> CurrentUser:
    return CurrentUser(id="user-id", role="user")


def override_service_client() -> FakeServiceClient:
    return FakeServiceClient()


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_catalog_read_is_public() -> None:
    app.dependency_overrides[get_service_client] = override_service_client

    try:
        with TestClient(app) as client:
            response = client.get("/v1/products")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


def test_catalog_write_requires_seller() -> None:
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            response = client.post("/v1/products", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_seller_can_write_catalog() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="seller-id",
        role="seller",
    )
    app.dependency_overrides[get_service_client] = override_service_client

    try:
        with TestClient(app) as client:
            created = client.post("/v1/products", json={})
            updated = client.patch("/v1/products/product-id", json={})
            image_uploaded = client.put(
                "/v1/products/product-id/image",
                files={"image": ("product.png", b"image", "image/png")},
            )
            deleted = client.delete("/v1/products/product-id")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 200
    assert updated.status_code == 200
    assert image_uploaded.status_code == 200
    assert deleted.status_code == 200


def test_inventory_commands_are_not_exposed() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/products/product-id/reserve", json={"quantity": 1})

    assert response.status_code == 405


def test_analytics_requires_admin() -> None:
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            response = client.get("/v1/analytics/overview")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_can_read_analytics() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="admin-id",
        role="admin",
    )
    app.dependency_overrides[get_service_client] = override_service_client

    try:
        with TestClient(app) as client:
            response = client.get("/v1/analytics/overview")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"service_url": settings.services.analytics_url}


def test_registration_is_public_and_reaches_auth_service() -> None:
    app.dependency_overrides[get_service_client] = override_service_client

    try:
        with TestClient(app) as client:
            response = client.post("/v1/auth/register", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"service_url": settings.services.auth_url}


def test_orders_require_access_token() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/orders")

    assert response.status_code == 401


def test_authenticated_request_reaches_order_service() -> None:
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_service_client] = override_service_client

    try:
        with TestClient(app) as client:
            response = client.get("/v1/orders")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"service_url": settings.services.order_url}


def test_order_status_update_is_not_exposed() -> None:
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/v1/orders/order-id",
                json={"status": "paid"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 405


def test_order_item_update_reaches_order_service() -> None:
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_service_client] = override_service_client

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/v1/orders/order-id/items/item-id",
                json={"quantity": 2},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


def test_authenticated_request_reaches_payment_service() -> None:
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_service_client] = override_service_client

    try:
        with TestClient(app) as client:
            response = client.get("/v1/payments?order_id=order-id")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"service_url": settings.services.payment_url}


def test_payment_creation_is_not_exposed() -> None:
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            response = client.post("/v1/payments", json={})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 405


def test_payment_status_update_is_not_exposed() -> None:
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            response = client.patch(
                "/v1/payments/payment-id/status",
                json={"status": "succeeded"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_authenticated_request_reaches_notification_service() -> None:
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_service_client] = override_service_client

    try:
        with TestClient(app) as client:
            response = client.get("/v1/notifications/users/user-id")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"service_url": settings.services.notification_url}
