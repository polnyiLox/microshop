from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import RedisError

from app.cache import RedisCache


@pytest.mark.asyncio
async def test_failed_connection_disables_cache() -> None:
    client = AsyncMock()
    client.ping.side_effect = RedisError("unavailable")
    cache = RedisCache(SimpleNamespace(url="redis://redis:6379/0"))

    with patch("app.cache.redis.Redis.from_url", return_value=client):
        await cache.connect()

    assert cache._client is None
    client.aclose.assert_awaited_once()
