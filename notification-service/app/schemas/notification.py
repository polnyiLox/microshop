from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import NotificationStatusEnum


class NotificationRead(BaseModel):
    id: str
    message: dict
    user_id: str
    status: NotificationStatusEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
