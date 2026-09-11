from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.enums import UserRole
from app.repositories import (
    BalanceOperationRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.schemas import LoginEmailSchema, RegisterSchema
from app.services import AuthService, BalanceService


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_repository_persists_and_finds_user(session: AsyncSession) -> None:
    repository = UserRepository(session)

    created = await repository.create(
        email="repo@example.com",
        phone_number="+79990000001",
        hashed_password="hash",
    )

    assert await repository.get_by_id(created.id) is created
    assert await repository.get_by_email("repo@example.com") is created
    assert await repository.get_by_phone_number("+79990000001") is created
    assert created.role == UserRole.USER


async def test_service_registers_and_logs_in_with_postgres(session: AsyncSession) -> None:
    users = UserRepository(session)
    refresh_tokens = RefreshTokenRepository(session)
    service = AuthService(session, users, refresh_tokens, settings.jwt_auth)
    registration = RegisterSchema(
        email="flow@example.com",
        phone_number="+79990000002",
        password="correct-password",
    )

    user = await service.register(registration)
    tokens = await service.login_email(LoginEmailSchema(
        email=registration.email,
        password=registration.password,
    ))

    stored_tokens = await refresh_tokens.get_by_user_id(user.id)
    assert tokens["access_token"]
    assert len(stored_tokens) == 1
    assert not stored_tokens[0].is_revoked


async def test_balance_service_is_idempotent_with_postgres(
    session: AsyncSession,
) -> None:
    users = UserRepository(session)
    user = await users.create(
        email="balance@example.com",
        phone_number="+79990000004",
        hashed_password="hash",
    )
    user.balance = 1_000
    await session.commit()

    cache = AsyncMock()
    cache.create_balance_key = Mock(
        side_effect=lambda user_id: f"balance:{user_id}",
    )
    service = BalanceService(
        session,
        users,
        BalanceOperationRepository(session),
        cache,
        SimpleNamespace(redis=SimpleNamespace(ttl_seconds=60)),
    )

    first_result = await service.debit(user.id, 300, "payment:test")
    repeated_result = await service.debit(user.id, 300, "payment:test")
    stored_user = await users.get_by_id(user.id)

    assert first_result.balance == 700
    assert repeated_result.balance == 700
    assert stored_user is not None
    assert stored_user.balance == 700
