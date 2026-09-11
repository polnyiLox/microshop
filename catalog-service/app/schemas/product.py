from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_image_url(value: str) -> str:
    value = value.strip()
    if not value:
        return value

    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Image must be an absolute HTTP or HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Image URL must not contain credentials")
    return value


class ProductBase(BaseModel):
    name: str = Field(..., min_length=5, max_length=510)
    description: str
    price: int = Field(..., ge=0)
    quantity: int = Field(..., ge=0)
    category: str = Field(..., max_length=255)


class ProductCreate(ProductBase):
    seller_id: str
    image: str = Field(default="", max_length=2048)

    @field_validator("image")
    @classmethod
    def validate_image_url(cls, value: str) -> str:
        return normalize_image_url(value)


class ProductCreateRequest(ProductBase):
    image: str = Field(default="", max_length=2048)

    @field_validator("image")
    @classmethod
    def validate_image_url(cls, value: str) -> str:
        return normalize_image_url(value)


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=5, max_length=510)
    description: str | None = None
    price: int | None = Field(None, ge=0)
    quantity: int | None = Field(None, ge=0)
    image: str | None = Field(None, max_length=2048)
    category: str | None = Field(None, max_length=255)

    @field_validator("image")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        return None if value is None else normalize_image_url(value)


class ProductRead(ProductBase):
    id: str
    seller_id: str
    image: str = ""

    model_config = ConfigDict(from_attributes=True)
