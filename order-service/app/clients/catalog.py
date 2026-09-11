import httpx
from httpx import HTTPStatusError, TimeoutException, RequestError

from app.exceptions import ProductNotFoundError, CatalogServiceUnavailableError, NotEnoughProductError



class CatalogClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def get_product(self, product_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self._base_url}/products/{product_id}")
                response.raise_for_status()
                return response.json()
            except HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ProductNotFoundError()
                raise CatalogServiceUnavailableError(
                    f"Catalog service error: {e.response.status_code}"
                )
            except TimeoutException:
                raise CatalogServiceUnavailableError(
                    f"Catalog service timeout for product {product_id}"
                )
            except RequestError as e:
                raise CatalogServiceUnavailableError(
                    f"Catalog service unavailable: {str(e)}"
                )

    async def reserve_product(self, product_id: str, quantity: int) -> dict:
        """Reserve stock or translate catalog failures into domain errors."""
        async  with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self._base_url}/products/{product_id}/reserve",
                    params={"quantity": quantity},
                )

                if response.status_code == 409:
                    raise NotEnoughProductError()

                response.raise_for_status()
                return response.json()
            except HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ProductNotFoundError() from None
                raise CatalogServiceUnavailableError(
                    f"Catalog service error: {e.response.status_code}"
                ) from None
            except TimeoutException:
                raise CatalogServiceUnavailableError(
                    f"Catalog service timeout for product {product_id}"
                )
            except RequestError as e:
                raise CatalogServiceUnavailableError(
                    f"Catalog service unavailable: {str(e)}"
                )

    async def release_product(self, product_id: str, quantity: int) -> None:
        """Release stock or translate catalog failures into domain errors."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self._base_url}/products/{product_id}/release",
                    params={"quantity": quantity}
                )
                response.raise_for_status()
            except HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ProductNotFoundError() from None
                raise CatalogServiceUnavailableError(
                    f"Catalog service error: {e.response.status_code}"
                ) from None
            except TimeoutException:
                raise CatalogServiceUnavailableError(
                    f"Catalog service timeout for product {product_id}"
                )
            except RequestError as e:
                raise CatalogServiceUnavailableError(
                    f"Catalog service unavailable: {str(e)}"
                )
