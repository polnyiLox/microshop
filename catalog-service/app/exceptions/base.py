class AppError(Exception):
    """Base error of all app"""
    status_code: int = 500
    detail: str = "App error"