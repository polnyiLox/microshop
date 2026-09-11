class AppError(Exception):
    status_code: int = 500
    detail: str = "Application error"
