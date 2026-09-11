from enum import StrEnum


class OrderStatusEnum(StrEnum):
    CREATED = "created"
    WAITING_PAYMENT = "waiting_payment"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    
    @classmethod
    def active_statuses(cls) -> list['OrderStatusEnum']:
        """Статусы, когда заказ активен и можно редактировать"""
        return [cls.CREATED, cls.WAITING_PAYMENT]
    
    @classmethod
    def final_statuses(cls) -> list['OrderStatusEnum']:
        """Финальные статусы, после которых нельзя редактировать"""
        return [cls.CLOSED, cls.CANCELLED, cls.FAILED]
    
    def can_edit(self) -> bool:
        """Можно ли редактировать заказ с этим статусом"""
        return self in self.active_statuses()
    
    def is_final(self) -> bool:
        """Финальный ли статус"""
        return self in self.final_statuses()

    @property
    def allowed_transitions(self) -> list['OrderStatusEnum']:
        """Какие статусы доступны из текущего"""
        transitions = {
            self.CREATED: [self.WAITING_PAYMENT, self.CANCELLED, self.FAILED],
            self.WAITING_PAYMENT: [self.PAID, self.CANCELLED, self.FAILED],
            self.PAID: [self.SHIPPED, self.CANCELLED],
            self.SHIPPED: [self.DELIVERED],
            self.DELIVERED: [self.CLOSED],
            self.CLOSED: [],
            self.CANCELLED: [],
            self.FAILED: [],
        }
        return transitions.get(self, [])

    def can_transition_to(self, new_status: 'OrderStatusEnum') -> bool:
        """Можно ли перейти в новый статус"""
        return new_status in self.allowed_transitions
