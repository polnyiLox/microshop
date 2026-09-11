from app.core.config import settings
from app.enums import UserRole
from app.exceptions import InvalidAccessTokenError
from app.schemas import CurrentUser

from .access_token import decode_access_token, load_key


def get_user_from_access_token(access_token: str) -> CurrentUser:
    payload = decode_access_token(
        access_token=access_token,
        key=load_key(settings.jwt.public_key_path),
        algorithm=settings.jwt.algorithm,
    )

    user_id = payload.get("sub")
    role = payload.get("role")

    if not isinstance(user_id, str) or not user_id:
        raise InvalidAccessTokenError()

    if not isinstance(role, str) or role not in UserRole:
        raise InvalidAccessTokenError()

    return CurrentUser(id=user_id, role=UserRole(role))
