import asyncio
from datetime import UTC, datetime, timedelta
import logging
from typing import TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AuthJWTSettings
from app.db.models import RefreshToken, User
from app.enums import UserRole
from app.exceptions import (
    EmailNotFoundError,
    EmailAlreadyExistsError,
    IncorrectPasswordError,
    InvalidRefreshTokenError,
    PhoneNumberAlreadyExistsError,
    PhoneNumberNotFoundError,
    RefreshTokenExpiredError,
    RefreshTokenRevokedError,
    UserNotFoundError,
)
from app.repositories import RefreshTokenRepository, UserRepository
from app.schemas import (
    LoginEmailSchema,
    LoginPhoneNumberSchema,
    RegisterSchema,
    UserRead,
)
from app.security.access_token import create_access_token, load_key
from app.security.password import hash_password, verify_password
from app.security.refresh_token import (
    create_refresh_token,
    hash_refresh_token,
)


logger = logging.getLogger(__name__)


class TokenPair(TypedDict):
    access_token: str
    refresh_token: str


class AuthService:
    """Coordinate credentials, JWT issuance and refresh-token persistence."""

    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        settings: AuthJWTSettings,
    ) -> None:
        self._session = session
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._settings = settings

        self._private_key = load_key(settings.private_key_path)

    async def _check_phone_number_unique(self, phone_number: str) -> None:
        existing_user = await self._user_repo.get_by_phone_number(phone_number)
        if existing_user is not None:
            logger.warning("Registration rejected: phone number already exists")
            raise PhoneNumberAlreadyExistsError()

    async def _check_email_unique(self, email: str) -> None:
        existing_user = await self._user_repo.get_by_email(email)
        if existing_user is not None:
            logger.warning("Registration rejected: email already exists")
            raise EmailAlreadyExistsError()

    async def _get_existing_user_by_email(self, email: str) -> User:
        user = await self._user_repo.get_by_email(email)
        if user is None:
            logger.warning("Email login rejected: user not found")
            raise EmailNotFoundError()
        return user

    async def _get_existing_user_by_phone_number(self, phone_number: str) -> User:
        user = await self._user_repo.get_by_phone_number(phone_number)
        if user is None:
            logger.warning("Phone login rejected: user not found")
            raise PhoneNumberNotFoundError()
        return user

    async def _get_existing_user_by_id(self, user_id: str) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            logger.warning("User not found user_id=%s", user_id)
            raise UserNotFoundError()
        return user

    async def _get_existing_refresh_token(self, refresh_token_hash: str) -> RefreshToken:
        refresh_token = await self._refresh_token_repo.get_by_token_hash(refresh_token_hash)
        if refresh_token is None:
            logger.warning("Refresh token rejected: token not found")
            raise InvalidRefreshTokenError()
        return refresh_token

    async def _create_tokens(self, user: User) -> TokenPair:
        logger.debug("Creating token pair user_id=%s", user.id)
        refresh_token = create_refresh_token()
        refresh_token_hash = hash_refresh_token(refresh_token)

        access_token = await asyncio.to_thread(
            create_access_token,
            {"sub": user.id, "role": user.role.value},
            self._private_key,
            self._settings.access_token_expire_minutes,
            self._settings.algorithm,
        )

        expires_at = datetime.now(UTC) + timedelta(
            days=self._settings.refresh_token_expire_days,
        )

        await self._refresh_token_repo.create(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=int(expires_at.timestamp()),
        )
        logger.debug("Token pair created user_id=%s", user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    async def _login(self, user: User, password: str) -> TokenPair:
        is_password_valid = await asyncio.to_thread(
            verify_password,
            password,
            user.hashed_password,
        )

        if not is_password_valid:
            logger.warning("Login rejected: incorrect password user_id=%s", user.id)
            raise IncorrectPasswordError()

        tokens = await self._create_tokens(user)
        await self._session.commit()
        logger.info("Login completed user_id=%s role=%s", user.id, user.role.value)
        return tokens

    async def register(self, register_data: RegisterSchema) -> UserRead:
        logger.info("Starting user registration")
        await self._check_phone_number_unique(register_data.phone_number)
        await self._check_email_unique(register_data.email)

        hashed_password = await asyncio.to_thread(
            hash_password,
            register_data.password,
        )

        new_user = await self._user_repo.create(
            email=register_data.email,
            phone_number=register_data.phone_number,
            hashed_password=hashed_password,
        )

        await self._session.commit()
        logger.info("User registration completed user_id=%s", new_user.id)
        return UserRead.model_validate(new_user)

    async def login_email(self, login_email_data: LoginEmailSchema) -> TokenPair:
        logger.info("Starting login with email credentials")
        user = await self._get_existing_user_by_email(login_email_data.email)
        return await self._login(user, login_email_data.password)

    async def login_phone_number(self, login_phone_number_data: LoginPhoneNumberSchema) -> TokenPair:
        logger.info("Starting login with phone credentials")
        user = await self._get_existing_user_by_phone_number(login_phone_number_data.phone_number)
        return await self._login(user, login_phone_number_data.password)

    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """Rotate a valid refresh token so every token can be used only once."""
        logger.info("Starting refresh token rotation")
        refresh_token_hash = hash_refresh_token(refresh_token)
        refresh_token_orm = await self._get_existing_refresh_token(refresh_token_hash)

        if refresh_token_orm.is_revoked:
            logger.warning(
                "Refresh token rejected: token revoked user_id=%s",
                refresh_token_orm.user_id,
            )
            raise RefreshTokenRevokedError()

        now_uix = int(datetime.now(UTC).timestamp())

        if now_uix >= refresh_token_orm.expires_at:
            logger.warning(
                "Refresh token rejected: token expired user_id=%s",
                refresh_token_orm.user_id,
            )
            raise RefreshTokenExpiredError()

        await self._refresh_token_repo.revoke_token(refresh_token_orm)

        user = await self._get_existing_user_by_id(refresh_token_orm.user_id)
        tokens = await self._create_tokens(user)
        await self._session.commit()
        logger.info("Refresh token rotation completed user_id=%s", user.id)
        return tokens

    async def logout(self, refresh_token: str) -> None:
        logger.info("Starting logout")
        refresh_token_hash = hash_refresh_token(refresh_token)
        refresh_token_orm = await self._get_existing_refresh_token(refresh_token_hash)

        await self._refresh_token_repo.revoke_token(refresh_token_orm)
        await self._session.commit()
        logger.info("Logout completed user_id=%s", refresh_token_orm.user_id)

    async def logout_all(self, user_id: str) -> None:
        logger.info("Starting logout from all sessions user_id=%s", user_id)
        await self._refresh_token_repo.revoke_all_user_tokens(user_id)
        await self._session.commit()
        logger.info("All sessions revoked user_id=%s", user_id)

    async def update_user_role(
            self,
            user_id: str,
            role: UserRole,
    ) -> UserRead:
        logger.info("Starting user role update user_id=%s role=%s", user_id, role.value)
        user = await self._get_existing_user_by_id(user_id)
        updated_user = await self._user_repo.update_role(user, role)
        await self._refresh_token_repo.revoke_all_user_tokens(user_id)
        await self._session.commit()
        logger.info("User role updated user_id=%s role=%s", user_id, role.value)
        return UserRead.model_validate(updated_user)
