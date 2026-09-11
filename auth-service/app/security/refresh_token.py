import hashlib
import secrets
from secrets import compare_digest


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def verify_refresh_token(refresh_token: str, refresh_token_hash: str) -> bool:
    return compare_digest(hash_refresh_token(refresh_token), refresh_token_hash)
