from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_payment_service
from app.core.config import PaymentEventsExchangeSettings
from app.main import app
from app.repositories import PaymentRepository
from app.services import PaymentService


@pytest.mark.asyncio(loop_scope="session")
async def test_create_list_and_cancel_payment(session: AsyncSession) -> None:
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_payment_key = Mock(side_effect=lambda payment_id: f"payment:{payment_id}")
    cache.create_order_payments_key = Mock(side_effect=lambda order_id: f"order:{order_id}")
    cache.create_user_payments_key = Mock(side_effect=lambda user_id: f"user:{user_id}")
    service = PaymentService(
        PaymentRepository(session),
        session,
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        PaymentEventsExchangeSettings(),
        cache,
        60,
    )
    app.dependency_overrides[get_payment_service] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/v1/payments",
                headers={"X-User-ID": "user-id"},
                json={"user_id": "spoofed", "order_id": "order-id", "amount": 500},
            )
            payment_id = created.json()["id"]
            listed = await client.get(
                "/v1/payments",
                headers={"X-User-ID": "user-id"},
                params={"order_id": "order-id"},
            )
            cancelled = await client.post(
                f"/v1/payments/{payment_id}/cancel",
                headers={"X-User-ID": "user-id"},
            )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["user_id"] == "user-id"
    assert [item["id"] for item in listed.json()] == [payment_id]
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


@pytest.mark.asyncio(loop_scope="session")
async def test_payment_api_hides_another_users_payment(
    session: AsyncSession,
) -> None:
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_payment_key = Mock(
        side_effect=lambda payment_id: f"payment:{payment_id}",
    )
    cache.create_order_payments_key = Mock(
        side_effect=lambda order_id: f"order:{order_id}",
    )
    cache.create_user_payments_key = Mock(
        side_effect=lambda user_id: f"user:{user_id}",
    )
    repository = PaymentRepository(session)
    service = PaymentService(
        repository,
        session,
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        PaymentEventsExchangeSettings(),
        cache,
        60,
    )
    app.dependency_overrides[get_payment_service] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/v1/payments",
                headers={"X-User-ID": "owner-id"},
                json={"user_id": "spoofed", "order_id": "private-order", "amount": 500},
            )
            payment_id = created.json()["id"]
            forbidden = await client.get(
                f"/v1/payments/{payment_id}",
                headers={"X-User-ID": "another-user"},
            )
            hidden_list = await client.get(
                "/v1/payments",
                headers={"X-User-ID": "another-user"},
                params={"order_id": "private-order"},
            )
    finally:
        app.dependency_overrides.clear()

    stored = await repository.get_by_id(payment_id)
    assert created.status_code == 201
    assert forbidden.status_code == 404
    assert hidden_list.status_code == 200
    assert hidden_list.json() == []
    assert stored is not None
    assert stored.user_id == "owner-id"
