from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return await self._session.scalar(query)

    async def get_by_user_id(self, user_id: str) -> list[RefreshToken]:
        query = select(RefreshToken).where(RefreshToken.user_id == user_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def create(self, user_id: str, token_hash: str, expires_at: int) -> RefreshToken:
        new_refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(new_refresh_token)
        await self._session.flush()
        return new_refresh_token

    async def revoke_token(self, token: RefreshToken) -> None:
        token.is_revoked = True
        await self._session.flush()

    async def revoke_all_user_tokens(self, user_id: str) -> None:
        stmt = update(RefreshToken).where(RefreshToken.user_id == user_id).values(is_revoked=True)
        await self._session.execute(stmt)
        await self._session.flush()

    async def delete(self, refresh_token: RefreshToken) -> None:
        await self._session.delete(refresh_token)
        await self._session.flush()

    async def delete_all_user_tokens(self, user_id: str) -> None:
        stmt = delete(RefreshToken).where(RefreshToken.user_id == user_id)
        await self._session.execute(stmt)
        await self._session.flush()
