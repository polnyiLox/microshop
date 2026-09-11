from .base import AppError


class OrderNotFoundError(AppError):
    status_code = 404
    detail = "Order not found"