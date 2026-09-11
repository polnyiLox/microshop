from app.enums import OrderStatusEnum


def test_order_status_transition_graph() -> None:
    assert OrderStatusEnum.CREATED.can_transition_to(OrderStatusEnum.WAITING_PAYMENT)
    assert not OrderStatusEnum.CREATED.can_transition_to(OrderStatusEnum.PAID)
    assert OrderStatusEnum.PAID.can_transition_to(OrderStatusEnum.SHIPPED)
    assert OrderStatusEnum.CANCELLED.is_final()
    assert not OrderStatusEnum.PAID.is_final()
    assert not OrderStatusEnum.DELIVERED.is_final()
    assert OrderStatusEnum.DELIVERED.can_transition_to(OrderStatusEnum.CLOSED)
