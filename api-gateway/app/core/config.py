from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).parent.parent.parent


class ApiSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080
    reload: bool = False
    v1_prefix: str = "/v1"


class LoggingSettings(BaseModel):
    level: str = "INFO"


class MiddlewareSettings(BaseModel):
    allow_origins: list[str] = ["*"]
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]
    allow_credentials: bool = False


class ServicesSettings(BaseModel):
    auth_url: str = "http://127.0.0.1:8000"
    catalog_url: str = "http://127.0.0.1:8001"
    order_url: str = "http://127.0.0.1:8002"
    payment_url: str = "http://127.0.0.1:8003"
    notification_url: str = "http://127.0.0.1:8004"
    analytics_url: str = "http://127.0.0.1:8005"


class JwtSettings(BaseModel):
    public_key_path: Path = BASE_DIR / "certs" / "jwt-public.pem"
    algorithm: str = "RS256"


class HttpClientSettings(BaseModel):
    timeout_seconds: float = 10.0


class Settings(BaseSettings):
    api: ApiSettings = ApiSettings()
    middleware: MiddlewareSettings = MiddlewareSettings()
    services: ServicesSettings = ServicesSettings()
    jwt: JwtSettings = JwtSettings()
    http_client: HttpClientSettings = HttpClientSettings()
    logging: LoggingSettings = LoggingSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_CONFIG__",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
