from pydantic import BaseModel

from app.enums import UserRole


class CurrentUser(BaseModel):
    id: str
    role: UserRole
