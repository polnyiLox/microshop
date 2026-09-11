import pytest
from pydantic import ValidationError

from app.schemas import ProductCreateRequest


def product_data(image: str) -> dict:
    return {
        "name": "Test product",
        "description": "description",
        "price": 100,
        "quantity": 1,
        "image": image,
        "category": "test",
    }


def test_image_url_is_trimmed() -> None:
    product = ProductCreateRequest.model_validate(
        product_data("  https://images.example.com/product.png  "),
    )

    assert product.image == "https://images.example.com/product.png"


@pytest.mark.parametrize(
    "image",
    ["product.png", "file:///tmp/product.png", "https://user:secret@example.com/a.png"],
)
def test_unsafe_image_url_is_rejected(image: str) -> None:
    with pytest.raises(ValidationError):
        ProductCreateRequest.model_validate(product_data(image))
