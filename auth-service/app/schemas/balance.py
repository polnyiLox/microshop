from pydantic import BaseModel, Field


class BalanceAmount(BaseModel):
    amount: int = Field(gt=0, le=1_000_000_000)


class InternalBalanceChange(BalanceAmount):
    reference: str = Field(min_length=1, max_length=255)


class BalanceRead(BaseModel):
    balance: int
