from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user_id, get_payment_service
from app.exceptions import PaymentNotFoundError
from app.schemas import PaymentCreate, PaymentRead, PaymentStatusUpdate
from app.services import PaymentService


router = APIRouter(prefix="/payments", tags=["Платежи"])


async def require_payment_owner(
    payment_id: str,
    current_user_id: str = Depends(get_current_user_id),
    service: PaymentService = Depends(get_payment_service),
) -> str:
    payment = await service.get_payment_by_id(payment_id)
    if payment.user_id != current_user_id:
        raise PaymentNotFoundError()
    return current_user_id


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: PaymentCreate,
    current_user_id: str = Depends(get_current_user_id),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentRead:
    trusted_payment_data = payment_data.model_copy(
        update={"user_id": current_user_id},
    )
    return await service.create_payment(payment_data=trusted_payment_data)


@router.get("", response_model=list[PaymentRead])
async def get_payments(
    order_id: str,
    current_user_id: str = Depends(get_current_user_id),
    service: PaymentService = Depends(get_payment_service),
) -> list[PaymentRead]:
    payments = await service.get_payments_by_order_id(order_id)
    return [payment for payment in payments if payment.user_id == current_user_id]


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: str,
    current_user_id: str = Depends(require_payment_owner),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentRead:
    return await service.get_payment_by_id(payment_id)


@router.patch("/{payment_id}/status", response_model=PaymentRead)
async def update_payment_status(
    payment_id: str,
    update_data: PaymentStatusUpdate,
    current_user_id: str = Depends(require_payment_owner),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentRead:
    return await service.update_payment_status(payment_id, update_data)


@router.post("/{payment_id}/complete", response_model=PaymentRead)
async def complete_payment(
        payment_id: str,
        current_user_id: str = Depends(require_payment_owner),
        service: PaymentService = Depends(get_payment_service),
) -> PaymentRead:
    return await service.complete_payment(payment_id)


@router.post("/{payment_id}/cancel", response_model=PaymentRead)
async def cancel_payment(
    payment_id: str,
    current_user_id: str = Depends(require_payment_owner),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentRead:
    return await service.cancel_payment(payment_id)


@router.post("/{payment_id}/retry", response_model=PaymentRead)
async def retry_payment(
    payment_id: str,
    current_user_id: str = Depends(require_payment_owner),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentRead:
    return await service.retry_payment(payment_id)
