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
    user: str = "payment_service"
    password: str = "change_me"
    host: str = "rabbitmq"
    port: int = 5672
    vhost: str = "/"

    @property
    def url(self) -> str:
        user = quote(self.user, safe="")
        password = quote(self.password, safe="")
        vhost = quote(self.vhost, safe="")
        return f"amqp://{user}:{password}@{self.host}:{self.port}/{vhost}"


class KafkaSettings(BaseModel):
    bootstrap_servers: str = "host.docker.internal:9092"
    client_id: str = "payment-service"
    acks: str = "all"


class AnalyticsTopicsSettings(BaseModel):
    payment_events_topic: str = "payment.analytics.events"


class AuthClientSettings(BaseModel):
    base_url: str = "http://auth-service:8000/v1/internal"
    internal_token: str = "change_me"


class RedisSettings(BaseModel):
    host: str = "redis"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ttl_seconds: int = 60
    key_prefix: str = "payment"
    payment_key: str = "payment:"
    order_payments_key: str = "order:"
    user_payments_key: str = "user:"

    @property
    def url(self) -> str:
        credentials = ""
        if self.password:
            credentials = f":{quote(self.password, safe='')}@"
        return f"redis://{credentials}{self.host}:{self.port}/{self.db}"


class ExchangeSettings(BaseModel):
    exchange_name: str
    exchange_type: str = "topic"


class PaymentEventsExchangeSettings(ExchangeSettings):
    exchange_name: str = "payment.events"
    payment_created_routing_key: str = "payment.created"
    payment_succeeded_routing_key: str = "payment.succeeded"
    payment_failed_routing_key: str = "payment.failed"
    payment_cancelled_routing_key: str = "payment.cancelled"
    payment_refunded_routing_key: str = "payment.refunded"


class PaymentCommandsExchangeSettings(ExchangeSettings):
    exchange_name: str = "payment.commands"
    queue_name: str = "payment.order.queue"
    create_routing_key: str = "payment.create"
    cancel_routing_key: str = "payment.cancel"
    refund_routing_key: str = "payment.refund"


class Settings(BaseSettings):
    db: DataBaseSettings
    api: ApiSettings
    rabbitmq: RabbitMQSettings = RabbitMQSettings()
    kafka: KafkaSettings = KafkaSettings()
    analytics_topics: AnalyticsTopicsSettings = AnalyticsTopicsSettings()
    auth_client: AuthClientSettings = AuthClientSettings()
    redis: RedisSettings = RedisSettings()
    payment_events_ex: PaymentEventsExchangeSettings = PaymentEventsExchangeSettings()
    payment_commands_ex: PaymentCommandsExchangeSettings = PaymentCommandsExchangeSettings()
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
