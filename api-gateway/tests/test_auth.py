from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jwt import encode

from app.api.dependencies import get_current_user
from app.exceptions import InvalidAccessTokenError
from app.schemas import CurrentUser
from app.security import decode_access_token


TEST_SECRET = "a-test-secret-that-is-longer-than-thirty-two-bytes"


def test_decode_access_token() -> None:
    now = datetime.now(UTC)
    token = encode(
        {
            "sub": "user-id",
            "role": "user",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        key=TEST_SECRET,
        algorithm="HS256",
    )

    payload = decode_access_token(token, TEST_SECRET, "HS256")

    assert payload["sub"] == "user-id"
    assert payload["role"] == "user"


def test_decode_access_token_rejects_missing_claims() -> None:
    token = encode(
        {"sub": "user-id"},
        key=TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, TEST_SECRET, "HS256")


def test_current_user_rejects_unknown_role() -> None:
    from app.security import get_user_from_access_token

    with patch(
        "app.security.current_user.decode_access_token",
        return_value={"sub": "user-id", "role": "superuser"},
    ):
        with pytest.raises(InvalidAccessTokenError):
            get_user_from_access_token("access-token")


@pytest.mark.asyncio
async def test_get_current_user_builds_user_from_token() -> None:
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="access-token",
    )
    current_user_from_token = CurrentUser(id="user-id", role="user")

    with patch(
        "app.api.dependencies.auth.get_user_from_access_token",
        return_value=current_user_from_token,
    ):
        current_user = await get_current_user(credentials)

    assert current_user.id == "user-id"
    assert current_user.role == "user"


@pytest.mark.asyncio
async def test_get_current_user_requires_token() -> None:
    with pytest.raises(HTTPException) as error:
        await get_current_user(None)

    assert error.value.status_code == 401
