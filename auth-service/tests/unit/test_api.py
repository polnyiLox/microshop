from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_auth_service, get_current_user, get_user_repository
from app.api.routers.v1.auth import (
    login_with_email,
    logout,
    refresh_tokens,
    register_user,
)
from app.main import app
from app.enums import UserRole
from app.schemas import LoginEmailSchema, RegisterSchema
from app.services import AuthService


@pytest.mark.asyncio
async def test_register_endpoint_delegates_to_service() -> None:
    service = AsyncMock()
    expected = SimpleNamespace(id="user-id")
    service.register.return_value = expected
    data = RegisterSchema(
        email="user@example.com",
        phone_number="+79991234567",
        password="test-password",
    )

    result = await register_user(data, service)

    assert result is expected
    service.register.assert_awaited_once_with(data)


@pytest.mark.asyncio
async def test_login_endpoint_sets_refresh_cookie() -> None:
    response = SimpleNamespace(set_cookie=Mock())
    service = AsyncMock()
    service.login_email.return_value = {
        "access_token": "access",
        "refresh_token": "refresh",
    }

    result = await login_with_email(
        response,
        LoginEmailSchema(email="user@example.com", password="test-password"),
        service,
    )

    assert result.access_token == "access"
    response.set_cookie.assert_called_once()
    assert response.set_cookie.call_args.kwargs["value"] == "refresh"


@pytest.mark.asyncio
async def test_logout_requires_refresh_cookie() -> None:
    request = SimpleNamespace(cookies={})
    response = SimpleNamespace(delete_cookie=Mock())
    service = AsyncMock()

    with pytest.raises(HTTPException) as error:
        await logout(request, response, service)

    assert error.value.status_code == 401
    service.logout.assert_not_awaited()
    response.delete_cookie.assert_not_called()


@pytest.mark.asyncio
async def test_logout_clears_refresh_cookie() -> None:
    request = SimpleNamespace(cookies={"refresh_token": "refresh"})
    response = SimpleNamespace(delete_cookie=Mock())
    service = AsyncMock()

    await logout(request, response, service)

    service.logout.assert_awaited_once_with("refresh")
    response.delete_cookie.assert_called_once_with("refresh_token")


@pytest.mark.asyncio
async def test_refresh_endpoint_rotates_refresh_cookie() -> None:
    request = SimpleNamespace(cookies={"refresh_token": "old-refresh"})
    response = SimpleNamespace(set_cookie=Mock())
    service = AsyncMock()
    service.refresh_tokens.return_value = {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
    }

    result = await refresh_tokens(request, response, service)

    assert result.access_token == "new-access"
    service.refresh_tokens.assert_awaited_once_with("old-refresh")
    assert response.set_cookie.call_args.kwargs["value"] == "new-refresh"


@pytest.mark.asyncio
async def test_me_resolves_current_user_through_declared_dependencies() -> None:
    user_repository = AsyncMock()
    user_repository.get_by_id.return_value = SimpleNamespace(
        id="user-id",
        email="user@example.com",
        phone_number="+79991234567",
        balance=0,
        role=UserRole.USER,
    )
    app.dependency_overrides[get_user_repository] = lambda: user_repository

    try:
        with patch(
            "app.api.dependencies.decode_access_token",
            return_value={"sub": "user-id"},
        ), patch("app.api.dependencies.load_key", return_value="public-key"):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/v1/auth/me",
                    headers={"Authorization": "Bearer access-token"},
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_only_admin_can_update_user_role() -> None:
    service = AsyncMock()
    service.update_user_role.return_value = SimpleNamespace(
        id="seller-id",
        email="seller@example.com",
        phone_number="+79991234567",
        balance=0,
        role=UserRole.SELLER,
    )
    app.dependency_overrides[get_auth_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        role=UserRole.USER,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            forbidden = await client.patch(
                "/v1/auth/users/seller-id/role",
                json={"role": "seller"},
            )

        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            role=UserRole.ADMIN,
        )
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            allowed = await client.patch(
                "/v1/auth/users/seller-id/role",
                json={"role": "seller"},
            )
    finally:
        app.dependency_overrides.clear()

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    service.update_user_role.assert_awaited_once_with(
        "seller-id",
        UserRole.SELLER,
    )
