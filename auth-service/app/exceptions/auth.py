from fastapi import status

from .base import AppError


class AuthError(AppError):
    status_code: int = status.HTTP_401_UNAUTHORIZED


class InvalidAccessTokenError(AuthError):
    detail: str = "Invalid access token"


class InvalidRefreshTokenError(AuthError):
    detail: str = "Invalid refresh token"


class RefreshTokenExpiredError(AuthError):
    detail: str = "Refresh token expired"


class RefreshTokenRevokedError(AuthError):
    detail: str = "Refresh token revoked"


class InvalidPhoneNumberError(AuthError):
    detail: str = "Invalid phone number"


class PhoneNumberNotFoundError(AuthError):
    detail: str = "Phone number not found"


class EmailNotFoundError(AuthError):
    detail: str = "Email not found"


class IncorrectPasswordError(AuthError):
    detail: str = "Incorrect password"