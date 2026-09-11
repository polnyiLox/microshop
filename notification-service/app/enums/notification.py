from enum import StrEnum


class NotificationStatusEnum(StrEnum):
    CREATED = "created"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELED = "canceled"

    def can_edit(self) -> bool:
        return self == self.CREATED

    @property
    def allowed_transitions(self) -> list['NotificationStatusEnum']:
        transitions = {
            self.CREATED: [self.SENT, self.DELIVERED, self.READ, self.FAILED, self.CANCELED],
            self.SENT: [self.DELIVERED, self.FAILED, self.CANCELED, self.READ],
            self.DELIVERED: [self.READ, self.FAILED],
            self.READ: [],
            self.FAILED: [],
            self.CANCELED: [],
        }
        return transitions.get(self, [])

    def can_transition_to(self, status_to: 'NotificationStatusEnum') -> bool:
        return status_to in self.allowed_transitions