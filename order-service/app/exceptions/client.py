from .base import AppError


class CatalogServiceUnavailableError(AppError):
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(*args)
        self.status_code: int = 500
        self.detail: str = message