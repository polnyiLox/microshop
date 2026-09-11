from .base import AppError

from app.enums import OrderStatusEnum


class OrderNotFoundError(AppError):
    """Exception raises when order is not found"""
    status_code: int = 404
    detail: str = "Order not found"


class OrderForbiddenToEditError(AppError):
    """Exception raises when client tries to edit order with forbidden status"""
    def __init__(self, order_status: OrderStatusEnum, *args: object) -> None:
        super().__init__(*args)
        self.status_code: int = 403
        self.detail: str = f"Forbidden to edit order with status: {order_status}"


class InvalidStatusTransitionError(AppError):
    """Exception raises when client tries to change order status to invalid status"""
    def __init__(
            self,
            order_status_from: OrderStatusEnum,
            order_status_to: OrderStatusEnum,
            *args: object
    ) -> None:
        super().__init__(*args)
        self.status_code: int = 403
        self.detail = f"Cannot transition from {order_status_from} to {order_status_to}"


class CannotCloseEmptyOrderError(AppError):
    """Exception raises when client tries to close empty order"""
    status_code: int = 403
    detail: str = "Cannot close order without items"