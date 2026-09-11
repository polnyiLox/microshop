from datetime import datetime

from pydantic import BaseModel


class AnalyticsEventSchema(BaseModel):
    event_id: str
    event_type: str
    event_version: int
    occurred_at: datetime
    producer: str
    payload: dict