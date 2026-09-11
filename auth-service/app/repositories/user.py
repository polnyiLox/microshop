from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.enums import UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: str) -> User | None:
        query = select(User).where(User.id == user_id)
        return await self._session.scalar(query)

    async def get_by_id_for_update(self, user_id: str) -> User | None:
        query = select(User).where(User.id == user_id).with_for_update()
        return await self._session.scalar(query)

    async def get_by_email(self, email: str) -> User | None:
        query = select(User).where(User.email == email)
        return await self._session.scalar(query)

    async def get_by_phone_number(self, phone_number: str) -> User | None:
        query = select(User).where(User.phone_number == phone_number)
        return await self._session.scalar(query)

    async def create(self, email: str, phone_number: str, hashed_password: str) -> User:
        new_user = User(
            email=email,
            phone_number=phone_number,
            hashed_password=hashed_password
        )
        self._session.add(new_user)
        await self._session.flush()
        return new_user

    async def delete(self, user: User) -> None:
        await self._session.delete(user)
        await self._session.flush()

    async def update_role(self, user: User, role: UserRole) -> User:
        user.role = role
        await self._session.flush()
        return user
