from functools import lru_cache
from urllib.parse import quote

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataBaseSettings(BaseModel):
    user: str
    password: str
    host: str
    port: int
    name: str

    @property
    def url(self) -> str:
        user = quote(self.user, safe="")
        password = quote(self.password, safe="")
        database = quote(self.name, safe="")
        return (
            f"postgresql+asyncpg://{user}:{password}@"
            f"{self.host}:{self.port}/{database}"
        )


class ApiSettings(BaseModel):
    v1_prefix: str
    host: str
    port: int
    reload: bool


class LoggingSettings(BaseModel):
    level: str = "INFO"


class RabbitMQSettings(BaseModel):
    user: str
    password: str
    host: str
    port: int
    vhost: str

    @property
    def url(self) -> str:
        user = quote(self.user, safe="")
        password = quote(self.password, safe="")
        vhost = quote(self.vhost, safe="")
        return f"amqp://{user}:{password}@{self.host}:{self.port}/{vhost}"


class ExchangeSettings(BaseModel):
    exchange_name: str
    exchange_type: str = "topic"


class PaymentEventsExchangeSettings(ExchangeSettings):
    exchange_name: str = "payment.events"
    payment_succeeded_routing_key: str = "payment.succeeded"
    payment_failed_routing_key: str = "payment.failed"
    payment_cancelled_routing_key: str = "payment.cancelled"
    payment_refunded_routing_key: str = "payment.refunded"
    notification_payment_queue_name: str = "notification.payment.queue"


class OrderEventsExchangeSettings(ExchangeSettings):
    exchange_name: str = "order.events"
    order_created_routing_key: str = "order.created"
    order_cancelled_routing_key: str = "order.cancelled"
    notification_order_queue_name: str = "notification.order.queue"


class RedisSettings(BaseModel):
    host: str = "redis"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ttl_seconds: int = 3600
    key_prefix: str = "notification"
    user_notifications_key: str = "user:"

    @property
    def url(self) -> str:
        credentials = ""
        if self.password:
            credentials = f":{quote(self.password, safe='')}@"
        return f"redis://{credentials}{self.host}:{self.port}/{self.db}"


class Settings(BaseSettings):
    db: DataBaseSettings
    api: ApiSettings
    rabbitmq: RabbitMQSettings
    payment_events_ex: PaymentEventsExchangeSettings = PaymentEventsExchangeSettings()
    order_events_ex: OrderEventsExchangeSettings = OrderEventsExchangeSettings()
    redis: RedisSettings = RedisSettings()
    logging: LoggingSettings = LoggingSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_CONFIG__",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
