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
    user: str = "catalog_service"
    password: str = "change_me"
    host: str = "rabbitmq"
    port: int = 5672
    vhost: str = "/"

    @property
    def url(self) -> str:
        return f"amqp://{quote(self.user, safe='')}:{quote(self.password, safe='')}@{self.host}:{self.port}/{quote(self.vhost, safe='')}"


class RedisSettings(BaseModel):
    host: str = "redis"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ttl_seconds: int = 60
    key_prefix: str = "catalog"

    @property
    def url(self) -> str:
        credentials = ""
        if self.password:
            credentials = f":{quote(self.password, safe='')}@"
        return f"redis://{credentials}{self.host}:{self.port}/{self.db}"


class ExchangeSettings(BaseModel):
    exchange_name: str
    exchange_type: str = "topic"


class CatalogCommandsExchangeSettings(ExchangeSettings):
    exchange_name: str = "catalog.commands"
    queue_name: str = "catalog.order.queue"
    reserve_routing_key: str = "inventory.reserve"
    release_routing_key: str = "inventory.release"
    confirm_routing_key: str = "inventory.confirm"


class CatalogEventsExchangeSettings(ExchangeSettings):
    exchange_name: str = "catalog.events"
    reserved_routing_key: str = "inventory.reserved"
    reservation_failed_routing_key: str = "inventory.reservation_failed"
    released_routing_key: str = "inventory.released"
    release_failed_routing_key: str = "inventory.release_failed"


class S3Settings(BaseModel):
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    endpoint_url: str = "http://minio:9000"
    public_endpoint_url: str = "http://localhost:9000"
    service_name: str = "s3"
    region_name: str = "us-east-1"
    bucket_name: str = "catalog-images"
    presigned_url_expire_seconds: int = 3600


class Settings(BaseSettings):
    db: DataBaseSettings
    api: ApiSettings
    rabbitmq: RabbitMQSettings = RabbitMQSettings()
    redis: RedisSettings = RedisSettings()
    catalog_commands_ex: CatalogCommandsExchangeSettings = CatalogCommandsExchangeSettings()
    catalog_events_ex: CatalogEventsExchangeSettings = CatalogEventsExchangeSettings()
    s3: S3Settings = S3Settings()
    logging: LoggingSettings = LoggingSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_CONFIG__",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
