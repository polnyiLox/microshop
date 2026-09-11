from .base import AppError


class OrderServiceUnavailableError(AppError):
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(*args)
        self.status_code: int = 500
        self.detail: str = message


class BalanceServiceUnavailableError(AppError):
    status_code = 503
    detail = "Balance service is unavailable"


class InsufficientBalanceError(AppError):
    status_code = 409
    detail = "Insufficient balance"
