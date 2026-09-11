from fastapi import APIRouter, Depends

from app.api.dependencies import get_balance_service, get_current_user
from app.db.models import User
from app.schemas import BalanceAmount, BalanceRead
from app.services import BalanceService


router = APIRouter(prefix="/auth/balance", tags=["Баланс"])


@router.get("", response_model=BalanceRead)
async def get_balance(
    current_user: User = Depends(get_current_user),
    service: BalanceService = Depends(get_balance_service),
) -> BalanceRead:
    return await service.get_balance(current_user.id)


@router.post("/deposit", response_model=BalanceRead)
async def deposit_balance(
    data: BalanceAmount,
    current_user: User = Depends(get_current_user),
    service: BalanceService = Depends(get_balance_service),
) -> BalanceRead:
    return await service.deposit(current_user.id, data.amount)


@router.post("/withdraw", response_model=BalanceRead)
async def withdraw_balance(
    data: BalanceAmount,
    current_user: User = Depends(get_current_user),
    service: BalanceService = Depends(get_balance_service),
) -> BalanceRead:
    return await service.withdraw(current_user.id, data.amount)
