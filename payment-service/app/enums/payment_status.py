from enum import StrEnum


class PaymentStatusEnum(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

    @property
    def is_final(self) -> bool:
        return self in {
            PaymentStatusEnum.FAILED,
            PaymentStatusEnum.CANCELLED,
            PaymentStatusEnum.REFUNDED,
        }

    def can_transition_to(self, new_status: "PaymentStatusEnum") -> bool:
        transitions = {
            PaymentStatusEnum.PENDING: {
                PaymentStatusEnum.PROCESSING,
                PaymentStatusEnum.CANCELLED,
            },
            PaymentStatusEnum.PROCESSING: {
                PaymentStatusEnum.SUCCEEDED,
                PaymentStatusEnum.FAILED,
                PaymentStatusEnum.CANCELLED,
            },
            PaymentStatusEnum.SUCCEEDED: {PaymentStatusEnum.REFUNDED},
            PaymentStatusEnum.FAILED: set(),
            PaymentStatusEnum.CANCELLED: set(),
            PaymentStatusEnum.REFUNDED: set(),
        }
        return new_status in transitions[self]
