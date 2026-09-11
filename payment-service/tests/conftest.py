from collections.abc import AsyncGenerator, Generator
import os

os.environ.update({
    "APP_CONFIG__DB__USER": "test",
    "APP_CONFIG__DB__PASSWORD": "test",
    "APP_CONFIG__DB__HOST": "localhost",
    "APP_CONFIG__DB__PORT": "5432",
    "APP_CONFIG__DB__NAME": "test",
    "APP_CONFIG__API__V1_PREFIX": "/v1",
    "APP_CONFIG__API__HOST": "127.0.0.1",
    "APP_CONFIG__API__PORT": "8003",
    "APP_CONFIG__API__RELOAD": "false",
})

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.community.postgres import PostgresContainer


# ============================================================
# PostgreSQL
# ============================================================

@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """
    Один PostgreSQL container на весь test session.
    """

    with PostgresContainer(
        "postgres:17",
        username="test",
        password="test",
        dbname="test",
    ) as postgres:
        yield postgres


@pytest.fixture(scope="session")
def database_url(
    postgres_container: PostgresContainer,
) -> str:
    """
    Получаем URL PostgreSQL и переводим его
    с psycopg2 на asyncpg.
    """

    url = postgres_container.get_connection_url()

    return url.replace(
        "postgresql+psycopg2://",
        "postgresql+asyncpg://",
    )


# ============================================================
# Database migrations
# ============================================================

@pytest.fixture(scope="session")
def apply_migrations(database_url: str) -> None:
    """
    Применяем Alembic migrations один раз
    перед запуском integration/e2e тестов.
    """

    from app.core.config import settings

    parsed_url = make_url(database_url)
    settings.db.user = parsed_url.username or "test"
    settings.db.password = parsed_url.password or "test"
    settings.db.host = parsed_url.host or "localhost"
    settings.db.port = parsed_url.port or 5432
    settings.db.name = parsed_url.database or "test"

    config = Config("alembic.ini")

    config.set_main_option(
        "sqlalchemy.url",
        database_url,
    )

    command.upgrade(config, "head")


# ============================================================
# SQLAlchemy Engine
# ============================================================

@pytest_asyncio.fixture(
    scope="session",
    loop_scope="session",
)
async def engine(
    database_url: str,
    apply_migrations: None,
) -> AsyncGenerator[AsyncEngine, None]:
    """
    Один AsyncEngine на весь test session.
    """

    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
    )

    yield engine

    await engine.dispose()


# ============================================================
# Database session
# ============================================================

@pytest_asyncio.fixture(loop_scope="session")
async def session(
    engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Каждый тест получает собственную транзакцию.

    После теста транзакция откатывается,
    поэтому тесты изолированы друг от друга.
    """

    async with engine.connect() as connection:

        transaction = await connection.begin()

        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session

        finally:
            await session.close()
            await transaction.rollback()
