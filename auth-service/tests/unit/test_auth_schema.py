import pytest
from pydantic import ValidationError

from app.schemas import LoginEmailSchema, RegisterSchema


def test_registration_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        RegisterSchema(
            email="user@example.com",
            phone_number="+79990000000",
            password="short",
        )


def test_login_rejects_unreasonably_long_password() -> None:
    with pytest.raises(ValidationError):
        LoginEmailSchema(
            email="user@example.com",
            password="x" * 129,
        )
