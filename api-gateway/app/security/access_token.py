from functools import lru_cache
from pathlib import Path

from jwt import InvalidTokenError, decode

from app.exceptions import InvalidAccessTokenError


@lru_cache
def load_key(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def decode_access_token(
    access_token: str,
    key: str,
    algorithm: str,
) -> dict[str, object]:
    try:
        return decode(
            access_token,
            key=key,
            algorithms=[algorithm],
            options={"require": ["sub", "role", "iat", "exp"]},
        )
    except InvalidTokenError:
        raise InvalidAccessTokenError() from None

