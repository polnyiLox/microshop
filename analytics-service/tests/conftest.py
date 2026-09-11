from collections.abc import AsyncGenerator, Generator
import os

os.environ.update({
    "APP_CONFIG__MONGODB__USER": "test",
    "APP_CONFIG__MONGODB__PASSWORD": "test",
    "APP_CONFIG__MONGODB__HOST": "localhost",
    "APP_CONFIG__MONGODB__PORT": "27017",
    "APP_CONFIG__MONGODB__NAME": "test",
    "APP_CONFIG__MONGODB__AUTH_SOURCE": "admin",
    "APP_CONFIG__API__V1_PREFIX": "/v1",
    "APP_CONFIG__API__HOST": "127.0.0.1",
    "APP_CONFIG__API__PORT": "8005",
    "APP_CONFIG__API__RELOAD": "false",
})

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from testcontainers.community.mongodb import MongoDbContainer

from app.db.indexes import create_indexes


@pytest.fixture(scope="session")
def mongodb_container() -> Generator[MongoDbContainer, None, None]:
    with MongoDbContainer(
            image="mongo:8.0",
            username="test",
            password="test",
            dbname="test",
    ) as mongodb:
        yield mongodb


@pytest_asyncio.fixture(
    scope="session",
    loop_scope="session",
)
async def database(
        mongodb_container: MongoDbContainer,
) -> AsyncGenerator[AsyncDatabase, None]:
    client = AsyncMongoClient(mongodb_container.get_connection_url())
    database = client["test"]
    await database.command("ping")
    await create_indexes(database)

    try:
        yield database
    finally:
        await client.drop_database("test")
        await client.close()


@pytest_asyncio.fixture(loop_scope="session")
async def clean_database(database: AsyncDatabase) -> AsyncGenerator[None, None]:
    await database["analytics_events"].delete_many({})
    yield
    await database["analytics_events"].delete_many({})
