from app.enums import PaymentStatusEnum


def test_succeeded_payment_is_refundable() -> None:
    assert not PaymentStatusEnum.SUCCEEDED.is_final
    assert PaymentStatusEnum.SUCCEEDED.can_transition_to(
        PaymentStatusEnum.REFUNDED,
    )


def test_terminal_payment_statuses_are_final() -> None:
    assert PaymentStatusEnum.FAILED.is_final
    assert PaymentStatusEnum.CANCELLED.is_final
    assert PaymentStatusEnum.REFUNDED.is_final
