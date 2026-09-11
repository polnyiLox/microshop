from fastapi import APIRouter, Depends

from app.api.dependencies import get_balance_service, require_internal_token
from app.schemas import BalanceRead, InternalBalanceChange
from app.services import BalanceService


router = APIRouter(
    prefix="/internal/users/{user_id}/balance",
    tags=["Внутренний баланс"],
    dependencies=[Depends(require_internal_token)],
)


@router.post("/debit", response_model=BalanceRead)
async def debit_balance(
    user_id: str,
    data: InternalBalanceChange,
    service: BalanceService = Depends(get_balance_service),
) -> BalanceRead:
    return await service.debit(user_id, data.amount, data.reference)


@router.post("/credit", response_model=BalanceRead)
async def credit_balance(
    user_id: str,
    data: InternalBalanceChange,
    service: BalanceService = Depends(get_balance_service),
) -> BalanceRead:
    return await service.credit(user_id, data.amount, data.reference)
