from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    async_sessionmaker, 
    AsyncSession
)

from app.core.config import settings


engine = create_async_engine(
    url=settings.db.url
)
SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def engine_dispose() -> None:
    await engine.dispose()