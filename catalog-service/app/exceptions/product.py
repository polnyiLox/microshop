from .base import AppError


class ProductNotFoundError(AppError):
    """Exception raises when product is not found"""
    status_code = 404
    detail = "Product not found"


class NotEnoughProductError(AppError):
    """Exception raises when product not enough"""
    status_code: int = 409
    detail: str = "Not enough product"


class ProductForbiddenError(AppError):
    status_code = 403
    detail = "Only the product seller can modify this product"


class ProductImageError(AppError):
    """Raised when an uploaded product image is invalid."""

    status_code = 422
    detail = "Image must be JPEG, PNG or WebP and no larger than 5 MB"
