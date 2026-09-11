from abc import ABC, abstractmethod


class Cache(ABC):
    """Transport-independent cache contract used by the service layer."""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Return a cached value or ``None`` when the key is absent."""

    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Store a value for a limited amount of time."""

    @abstractmethod
    async def delete(self, *keys: str) -> None:
        """Remove one or more keys from the cache."""
