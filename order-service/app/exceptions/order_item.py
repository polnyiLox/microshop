from .base import AppError


class OrderItemNotFoundError(AppError):
    """Exception raises when order item is not found"""
    status_code: int = 404
    detail: str = "Order item not found"


class NotEnoughProductError(AppError):
    """Exception raises when quantity of product is not enough for order"""
    status_code: int = 409
    detail: str = "Quantity of product is not enough for order"


class OrderItemAlreadyExistsError(AppError):
    """Exception raises when client tries to add the same product in order"""
    status_code: int = 409
    detail: str = "This product is already in order"


class ProductNotFoundError(AppError):
    """Exception raises when product not found"""
    status_code: int = 404
    detail: str = "Product you tried to add to order not found"


class IncorrectOrderError(AppError):
    """Exception raises when client tries to edit item from another order"""
    status_code: int = 403
    detail: str = "Order item belongs to another order"


class OwnProductOrderError(AppError):
    """Raised when a seller tries to buy a product owned by that seller."""

    status_code: int = 409
    detail: str = "Seller cannot order their own product"
