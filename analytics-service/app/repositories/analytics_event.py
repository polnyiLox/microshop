from pymongo.asynchronous.database import AsyncDatabase

from app.schemas import AnalyticsEventSchema


class AnalyticsEventRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._collection = database["analytics_events"]

    async def create(self, event: AnalyticsEventSchema) -> None:
        await self._collection.insert_one(
            event.model_dump(mode="python")
        )
