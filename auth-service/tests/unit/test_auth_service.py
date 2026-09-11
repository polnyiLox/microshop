from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.exceptions import (
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    RefreshTokenExpiredError,
)
from app.enums import UserRole
from app.schemas import LoginEmailSchema, RegisterSchema
from app.services import AuthService


def build_service() -> tuple[AuthService, AsyncMock, AsyncMock, AsyncMock]:
    session = AsyncMock()
    user_repo = AsyncMock()
    refresh_repo = AsyncMock()
    settings = SimpleNamespace(
        private_key_path="unused",
        algorithm="RS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
    )
    with patch("app.services.auth.load_key", return_value="private-key"):
        service = AuthService(session, user_repo, refresh_repo, settings)
    return service, session, user_repo, refresh_repo


@pytest.mark.asyncio
async def test_register_hashes_password_and_commits() -> None:
    service, session, user_repo, _ = build_service()
    user_repo.get_by_phone_number.return_value = None
    user_repo.get_by_email.return_value = None
    user_repo.create.return_value = SimpleNamespace(
        id="user-id",
        email="user@example.com",
        phone_number="+79991234567",
        balance=0,
        role=UserRole.USER,
    )
    data = RegisterSchema(
        email="user@example.com",
        phone_number="+79991234567",
        password="test-password",
    )

    with patch("app.services.auth.hash_password", return_value="hashed"):
        result = await service.register(data)

    user_repo.create.assert_awaited_once_with(
        email="user@example.com",
        phone_number="+79991234567",
        hashed_password="hashed",
    )
    session.commit.assert_awaited_once()
    assert result.id == "user-id"


@pytest.mark.asyncio
async def test_register_stops_when_email_exists() -> None:
    service, session, user_repo, _ = build_service()
    user_repo.get_by_phone_number.return_value = None
    user_repo.get_by_email.return_value = object()

    with pytest.raises(EmailAlreadyExistsError):
        await service.register(RegisterSchema(
            email="user@example.com",
            phone_number="+79991234567",
            password="test-password",
        ))

    user_repo.create.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_rejects_incorrect_password() -> None:
    service, session, user_repo, _ = build_service()
    user_repo.get_by_email.return_value = SimpleNamespace(
        id="user-id",
        hashed_password="hash",
    )

    with patch("app.services.auth.verify_password", return_value=False):
        with pytest.raises(IncorrectPasswordError):
            await service.login_email(LoginEmailSchema(
                email="user@example.com",
                password="wrong-password",
            ))

    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_puts_persisted_role_in_access_token() -> None:
    service, _, user_repo, _ = build_service()
    user_repo.get_by_email.return_value = SimpleNamespace(
        id="seller-id",
        hashed_password="hash",
        role=UserRole.SELLER,
    )

    with patch("app.services.auth.verify_password", return_value=True), patch(
        "app.services.auth.create_access_token",
        return_value="access-token",
    ) as create_token:
        await service.login_email(LoginEmailSchema(
            email="seller@example.com",
            password="test-password",
        ))

    assert create_token.call_args.args[0] == {
        "sub": "seller-id",
        "role": "seller",
    }


@pytest.mark.asyncio
async def test_admin_role_update_revokes_refresh_tokens() -> None:
    service, session, user_repo, refresh_repo = build_service()
    user = SimpleNamespace(
        id="user-id",
        email="user@example.com",
        phone_number="+79991234567",
        balance=0,
        role=UserRole.USER,
    )
    user_repo.get_by_id.return_value = user

    async def update_role(stored_user, role):
        stored_user.role = role
        return stored_user

    user_repo.update_role.side_effect = update_role

    result = await service.update_user_role("user-id", UserRole.SELLER)

    user_repo.update_role.assert_awaited_once_with(user, UserRole.SELLER)
    refresh_repo.revoke_all_user_tokens.assert_awaited_once_with("user-id")
    session.commit.assert_awaited_once()
    assert result.role == UserRole.SELLER


@pytest.mark.asyncio
async def test_refresh_rejects_expired_token_without_rotation() -> None:
    service, session, _, refresh_repo = build_service()
    refresh_repo.get_by_token_hash.return_value = SimpleNamespace(
        is_revoked=False,
        expires_at=int((datetime.now(UTC) - timedelta(seconds=1)).timestamp()),
        user_id="user-id",
    )

    with pytest.raises(RefreshTokenExpiredError):
        await service.refresh_tokens("refresh-token")

    refresh_repo.revoke_token.assert_not_awaited()
    session.commit.assert_not_awaited()
