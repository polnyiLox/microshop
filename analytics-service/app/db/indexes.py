from pymongo import ASCENDING
from pymongo.asynchronous.database import AsyncDatabase


async def create_indexes(database: AsyncDatabase) -> None:
    await database["analytics_events"].create_index(
        "event_id",
        unique=True
    )
    await database["analytics_events"].create_index("occurred_at")
    await database["analytics_events"].create_index(
        [
            ("event_type", ASCENDING),
            ("occurred_at", ASCENDING),
        ]
    )
