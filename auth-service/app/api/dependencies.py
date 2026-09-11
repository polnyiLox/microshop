from collections.abc import Callable
import secrets

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import RedisCache
from app.core.config import settings
from app.db.models import User
from app.enums import UserRole
from app.db.session import get_session
from app.exceptions import InvalidAccessTokenError
from app.repositories import BalanceOperationRepository, UserRepository, RefreshTokenRepository
from app.security.access_token import decode_access_token, load_key
from app.services import AuthService, BalanceService


redis_cache = RedisCache(settings.redis)


async def get_user_repository(
        session: AsyncSession = Depends(get_session),
) -> UserRepository:
    return UserRepository(session)


async def get_refresh_token_repository(
        session: AsyncSession = Depends(get_session),
) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)


async def get_balance_operation_repository(
    session: AsyncSession = Depends(get_session),
) -> BalanceOperationRepository:
    return BalanceOperationRepository(session)


async def get_balance_service(
    session: AsyncSession = Depends(get_session),
    user_repo: UserRepository = Depends(get_user_repository),
    operation_repo: BalanceOperationRepository = Depends(get_balance_operation_repository),
) -> BalanceService:
    return BalanceService(session, user_repo, operation_repo, redis_cache, settings)


async def require_internal_token(
    x_internal_token: str = Header(alias="X-Internal-Token"),
) -> None:
    if not secrets.compare_digest(x_internal_token, settings.internal_api.token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal token")


async def get_auth_service(
        session: AsyncSession = Depends(get_session),
        user_repo: UserRepository = Depends(get_user_repository),
        refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository)
) -> AuthService:
    return AuthService(
        session=session,
        user_repo=user_repo,
        refresh_token_repo=refresh_token_repo,
        settings=settings.jwt_auth
    )


schema = HTTPBearer(auto_error=False)


async def get_current_user(
        user_repository: UserRepository = Depends(get_user_repository),
        credentials: HTTPAuthorizationCredentials | None = Depends(schema),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_error

    try:
        payload = decode_access_token(
            access_token=str(credentials.credentials),
            key=load_key(settings.jwt_auth.public_key_path),
            algorithm=settings.jwt_auth.algorithm,
        )
    except InvalidAccessTokenError:
        raise credentials_error

    user_id = payload.get("sub", None)

    if user_id is None:
        raise credentials_error

    user = await user_repository.get_by_id(str(user_id))

    if user is None:
        raise credentials_error

    return user


def require_roles(*allowed_roles: UserRole) -> Callable[..., User]:
    async def role_checker(
            current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_checker
