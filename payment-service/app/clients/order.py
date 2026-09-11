import httpx
from httpx import TimeoutException, RequestError, HTTPStatusError

from app.exceptions import OrderServiceUnavailableError, OrderNotFoundError


class OrderClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def update_order_status(self, order_id: str, new_status: str) -> None:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    f"{self._base_url}/orders/{order_id}",
                    json={"status": new_status},
                )
                response.raise_for_status()
                return response.json()
            except HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise OrderNotFoundError()
                raise OrderServiceUnavailableError(
                    f"Order service error: {e.response.status_code}"
                )
            except TimeoutException:
                raise OrderServiceUnavailableError(
                    f"Order service timeout for order {order_id}"
                )
            except RequestError as e:
                raise OrderServiceUnavailableError(
                    f"Catalog service unavailable: {str(e)}"
                )
