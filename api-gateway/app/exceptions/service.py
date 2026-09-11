class ServiceUnavailableError(Exception):
    """Raised when a microservice cannot be reached."""


class ServiceTimeoutError(Exception):
    """Raised when a microservice takes too long to respond."""

