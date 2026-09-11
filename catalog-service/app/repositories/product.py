from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Product


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self) -> list[Product]:
        query = select(Product).order_by(Product.name)
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, product_id: str) -> Product | None:
        query = select(Product).where(Product.id == product_id)
        return await self._session.scalar(query)

    async def create(
            self, 
            name: str, 
            description: str, 
            price: int,
            quantity: int, 
            image_key: str | None,
            category: str,
            seller_id: str,
    ) -> Product:
        new_product = Product(
            name=name,
            description=description,
            price=price,
            quantity=quantity,
            image_key=image_key,
            category=category,
            seller_id=seller_id,
        )
        self._session.add(new_product)
        await self._session.flush()
        return new_product

    async def delete_product(self, product: Product) -> None:
        await self._session.delete(product)
        await self._session.flush()

    async def reserve_product(self, product_id: str, quantity: int) -> Product | None:
        """Atomically decrement stock only when the requested amount is available."""
        query = (
            update(Product)
            .where(
                Product.id == product_id,
                Product.quantity >= quantity
            )
            .values(quantity=Product.quantity - quantity)
            .returning(Product)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def release_product(self, product_id: str, quantity: int) -> Product | None:
        """
        Освободить товар (увеличить количество).
        """
        query = (
            update(Product)
            .where(Product.id == product_id)
            .values(quantity=Product.quantity + quantity)
            .returning(Product)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
