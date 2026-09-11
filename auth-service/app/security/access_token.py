from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from jwt import InvalidTokenError, decode, encode

from app.exceptions import InvalidAccessTokenError


@lru_cache
def load_key(path: Path) -> str:
    """Load a signing key once per process instead of once per request."""
    return path.read_text(encoding="utf-8")


def create_access_token(
        data: dict,
        key: str,
        expires_delta: int = 15,
        algorithm: str = "RS256",
) -> str:
    now = datetime.now(UTC)
    payload = data.copy()
    payload.update({"iat": now, "exp": now + timedelta(minutes=expires_delta)})
    return encode(
        payload=payload,
        key=key,
        algorithm=algorithm,
    )


def decode_access_token(
        access_token: str,
        key: str,
        algorithm: str = "RS256",
) -> dict[str, object]:
    try:
        return decode(
            access_token,
            key=key,
            algorithms=[algorithm],
        )
    except InvalidTokenError:
        raise InvalidAccessTokenError()
