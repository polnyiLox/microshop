from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_auth_service,
    get_balance_service,
    get_user_repository,
)
from app.core.config import settings
from app.main import app
from app.repositories import (
    BalanceOperationRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.services import AuthService, BalanceService


@pytest.mark.asyncio(loop_scope="session")
async def test_register_login_and_logout_flow(session: AsyncSession) -> None:
    service = AuthService(
        session,
        UserRepository(session),
        RefreshTokenRepository(session),
        settings.jwt_auth,
    )
    app.dependency_overrides[get_auth_service] = lambda: service
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="https://test") as client:
            registration = await client.post("/v1/auth/register", json={
                "email": "e2e@example.com",
                "phone_number": "+79990000003",
                "password": "correct-password",
            })
            login = await client.post("/v1/auth/login/email", json={
                "email": "e2e@example.com",
                "password": "correct-password",
            })
            logout_response = await client.post("/v1/auth/logout")
    finally:
        app.dependency_overrides.clear()

    assert registration.status_code == 200
    assert login.status_code == 200
    assert login.json()["access_token"]
    assert settings.refresh_token_cookies.key in login.cookies
    assert logout_response.status_code == 204


@pytest.mark.asyncio(loop_scope="session")
async def test_authenticated_balance_flow_persists_in_postgres(
    session: AsyncSession,
) -> None:
    users = UserRepository(session)
    auth_service = AuthService(
        session,
        users,
        RefreshTokenRepository(session),
        settings.jwt_auth,
    )
    cache = AsyncMock()
    cache.get.return_value = None
    cache.create_balance_key = Mock(
        side_effect=lambda user_id: f"balance:{user_id}",
    )
    balance_service = BalanceService(
        session,
        users,
        BalanceOperationRepository(session),
        cache,
        SimpleNamespace(redis=SimpleNamespace(ttl_seconds=60)),
    )
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_balance_service] = lambda: balance_service
    app.dependency_overrides[get_user_repository] = lambda: users

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="https://test",
        ) as client:
            registration = await client.post("/v1/auth/register", json={
                "email": "balance-e2e@example.com",
                "phone_number": "+79990000005",
                "password": "correct-password",
            })
            login = await client.post("/v1/auth/login/email", json={
                "email": "balance-e2e@example.com",
                "password": "correct-password",
            })
            authorization = {
                "Authorization": f"Bearer {login.json()['access_token']}"
            }
            deposit = await client.post(
                "/v1/auth/balance/deposit",
                headers=authorization,
                json={"amount": 1_000},
            )
            withdrawal = await client.post(
                "/v1/auth/balance/withdraw",
                headers=authorization,
                json={"amount": 250},
            )
            balance = await client.get(
                "/v1/auth/balance",
                headers=authorization,
            )
    finally:
        app.dependency_overrides.clear()

    user = await users.get_by_id(registration.json()["id"])
    assert registration.status_code == 200
    assert login.status_code == 200
    assert deposit.json() == {"balance": 1_000}
    assert withdrawal.json() == {"balance": 750}
    assert balance.json() == {"balance": 750}
    assert user is not None
    assert user.balance == 750
