import logging
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.exceptions import InvalidAccessTokenError
from app.enums import UserRole
from app.schemas import CurrentUser
from app.security import get_user_from_access_token


logger = logging.getLogger(__name__)


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        logger.warning("Authentication rejected: access token is missing")
        raise credentials_error

    try:
        return get_user_from_access_token(
            access_token=credentials.credentials,
        )
    except InvalidAccessTokenError:
        logger.warning("Authentication rejected: access token is invalid")
        raise credentials_error from None


def require_roles(*allowed_roles: UserRole) -> Callable[..., CurrentUser]:
    async def role_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role not in allowed_roles:
            logger.warning(
                "Authorization rejected: user_id=%s, role=%s, allowed_roles=%s",
                current_user.id,
                current_user.role,
                [role.value for role in allowed_roles],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker
