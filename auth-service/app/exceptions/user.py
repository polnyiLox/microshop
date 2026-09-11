from fastapi import status

from .base import AppError


class UserError(AppError):
    status_code: int = status.HTTP_409_CONFLICT


class PhoneNumberAlreadyExistsError(UserError):
    detail: str = "Phone number already exists"


class UserNotFoundError(AppError):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "User not found"


class EmailAlreadyExistsError(UserError):
    detail: str = "Email already exists"


class InsufficientBalanceError(UserError):
    detail: str = "Insufficient balance"


class BalanceReferenceConflictError(UserError):
    detail: str = "Balance operation reference conflicts with an existing operation"
