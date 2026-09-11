from pydantic import BaseModel, ConfigDict

from app.enums import UserRole


class UserRead(BaseModel):
    id: str
    email: str
    phone_number: str
    balance: int
    role: UserRole

    model_config = ConfigDict(
        from_attributes=True
    )


class UserRoleUpdate(BaseModel):
    role: UserRole
