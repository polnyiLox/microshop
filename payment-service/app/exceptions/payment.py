from .base import AppError


class PaymentNotFoundError(AppError):
    status_code = 404
    detail = "Payment not found"


class InvalidPaymentStatusTransitionError(AppError):
    status_code = 409

    def __init__(self, detail: str) -> None:
        self.detail = detail
