import logging
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.core.config import S3Settings
from app.core.s3_client import S3Client
from app.exceptions import (
    NotEnoughProductError,
    ProductForbiddenError,
    ProductImageError,
    ProductNotFoundError,
)
from app.db.models import Product
from app.repositories import ProductRepository
from app.schemas import ProductRead, ProductCreate, ProductUpdate


logger = logging.getLogger(__name__)


class ProductService:
    MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
    IMAGE_EXTENSIONS = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    def __init__(
            self, 
            product_repo: ProductRepository, 
            session: AsyncSession,
            cache: Cache,
            cache_ttl_seconds: int,
            s3_client: S3Client,
            s3_settings: S3Settings,
    ) -> None:
        self._product_repo = product_repo
        self._session = session
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._s3_client = s3_client
        self._s3_settings = s3_settings

    @staticmethod
    def _cache_key(product_id: str) -> str:
        return f"products:{product_id}"

    async def _invalidate_product(self, product_id: str) -> None:
        logger.debug("Invalidating product cache: product_id=%s", product_id)
        await self._cache.delete(self._cache_key(product_id))

    async def _get_existing_product(self, product_id: str) -> Product:
        product = await self._product_repo.get_by_id(product_id=product_id)
        if product is None:
            logger.warning("Product not found product_id=%s", product_id)
            raise ProductNotFoundError()
        return product

    @staticmethod
    def _is_s3_key(image_key: str | None) -> bool:
        return bool(image_key) and not image_key.startswith(("http://", "https://"))

    @classmethod
    def _create_image_key(cls, product_id: str, content_type: str) -> str:
        extension = cls.IMAGE_EXTENSIONS[content_type]
        return f"product-images/{product_id}/{uuid4()}{extension}"

    @classmethod
    def _validate_image(cls, content: bytes, content_type: str) -> None:
        if (
            not content
            or len(content) > cls.MAX_IMAGE_SIZE_BYTES
            or content_type not in cls.IMAGE_EXTENSIONS
        ):
            logger.warning(
                "Invalid product image content_type=%s size_bytes=%s",
                content_type,
                len(content),
            )
            raise ProductImageError()

    async def _save_file_to_s3(
        self,
        product_id: str,
        content: bytes,
        content_type: str,
    ) -> str:
        self._validate_image(content, content_type)
        image_key = self._create_image_key(product_id, content_type)
        logger.debug("Uploading product image to S3: key=%s, size=%d", image_key, len(content))
        try:
            await self._s3_client.upload_file(
                content=content,
                key=image_key,
                content_type=content_type,
            )
        except Exception:
            logger.exception("Product image upload failed: key=%s", image_key)
            raise
        logger.debug("Product image uploaded to S3: key=%s", image_key)
        return image_key

    async def _product_read_from_orm(self, product: Product) -> ProductRead:
        image = product.image_key or ""
        if self._is_s3_key(product.image_key):
            image = (
                await self._s3_client.generate_presigned_image_url(
                    key=product.image_key,
                )
                or ""
            )
        return ProductRead(
            id=product.id,
            name=product.name,
            description=product.description,
            price=product.price,
            quantity=product.quantity,
            category=product.category,
            seller_id=product.seller_id,
            image=image,
        )

    async def get_all_products(self) -> list[ProductRead]:
        logger.debug("Getting all products")
        products = await self._product_repo.get_all()
        result = [await self._product_read_from_orm(product) for product in products]
        logger.debug("Products loaded: count=%d", len(result))
        return result

    async def get_product_by_id(self, product_id: str) -> ProductRead:
        logger.debug("Getting product: product_id=%s", product_id)
        cache_key = self._cache_key(product_id)
        cached_product = await self._cache.get(cache_key)
        if cached_product is not None:
            logger.debug("Product cache hit: product_id=%s", product_id)
            try:
                return ProductRead.model_validate_json(cached_product)
            except ValidationError:
                logger.warning("Invalid product found in cache: product_id=%s", product_id)
                await self._cache.delete(cache_key)
        else:
            logger.debug("Product cache miss: product_id=%s", product_id)

        product = await self._get_existing_product(product_id=product_id)
        result = await self._product_read_from_orm(product)
        await self._cache.set(
            cache_key,
            result.model_dump_json(),
            min(
                self._cache_ttl_seconds,
                self._s3_settings.presigned_url_expire_seconds,
            ),
        )
        return result

    async def create_product(self, product_data: ProductCreate) -> ProductRead:
        logger.info("Creating product: seller_id=%s, name=%s", product_data.seller_id, product_data.name)
        new_product = await self._product_repo.create(
            name=product_data.name,
            description=product_data.description,
            price=product_data.price,
            quantity=product_data.quantity,
            image_key=product_data.image or None,
            category=product_data.category,
            seller_id=product_data.seller_id,
        )
        await self._session.commit()
        logger.info(
            "Product created product_id=%s seller_id=%s",
            new_product.id,
            new_product.seller_id,
        )
        return await self._product_read_from_orm(new_product)

    async def update_product(self, product_id: str, seller_id: str, update_data: ProductUpdate) -> ProductRead:
        logger.info("Updating product: product_id=%s, seller_id=%s", product_id, seller_id)
        product = await self._get_existing_product(product_id=product_id)
        if product.seller_id != seller_id:
            logger.warning(
                "Product update forbidden product_id=%s seller_id=%s",
                product_id,
                seller_id,
            )
            raise ProductForbiddenError()

        old_image_key = product.image_key
        changes = update_data.model_dump(exclude_unset=True)
        image = changes.pop("image", None)
        if image is not None:
            product.image_key = image or None

        for key, value in changes.items():
            if value is not None:
                setattr(product, key, value)

        await self._session.commit()
        await self._invalidate_product(product_id)
        if old_image_key != product.image_key and self._is_s3_key(old_image_key):
            await self._s3_client.delete_file(old_image_key)
        logger.info("Product updated product_id=%s seller_id=%s", product_id, seller_id)
        return await self._product_read_from_orm(product)

    async def upload_product_image(
        self,
        product_id: str,
        seller_id: str,
        content: bytes,
        content_type: str,
    ) -> ProductRead:
        """Upload or replace a product image owned by the current seller."""
        logger.info(
            "Uploading product image: product_id=%s, seller_id=%s, content_type=%s, size=%d",
            product_id,
            seller_id,
            content_type,
            len(content),
        )
        product = await self._get_existing_product(product_id=product_id)
        if product.seller_id != seller_id:
            logger.warning(
                "Product image upload forbidden product_id=%s seller_id=%s",
                product_id,
                seller_id,
            )
            raise ProductForbiddenError()

        old_image_key = product.image_key
        image_key = await self._save_file_to_s3(
            product_id=product_id,
            content=content,
            content_type=content_type,
        )
        product.image_key = image_key
        try:
            await self._session.commit()
        except Exception:
            logger.exception("Saving product image metadata failed: product_id=%s", product_id)
            await self._session.rollback()
            await self._s3_client.delete_file(image_key)
            raise

        await self._invalidate_product(product_id)
        if self._is_s3_key(old_image_key):
            await self._s3_client.delete_file(old_image_key)
        logger.info(
            "Product image uploaded product_id=%s seller_id=%s content_type=%s",
            product_id,
            seller_id,
            content_type,
        )
        return await self._product_read_from_orm(product)

    async def delete_product(self, product_id: str, seller_id: str) -> None:
        logger.info("Deleting product: product_id=%s, seller_id=%s", product_id, seller_id)
        product = await self._get_existing_product(product_id=product_id)
        if product.seller_id != seller_id:
            logger.warning(
                "Product deletion forbidden product_id=%s seller_id=%s",
                product_id,
                seller_id,
            )
            raise ProductForbiddenError()
        image_key = product.image_key
        await self._product_repo.delete_product(product=product)
        await self._session.commit()
        await self._invalidate_product(product_id)
        if self._is_s3_key(image_key):
            await self._s3_client.delete_file(image_key)
        logger.info("Product deleted product_id=%s seller_id=%s", product_id, seller_id)

    async def reserve_product(self, product_id: str, quantity: int) -> ProductRead:
        """Зарезервировать товар"""
        logger.info("Reserving product: product_id=%s, quantity=%d", product_id, quantity)
        product = await self._product_repo.reserve_product(product_id, quantity)

        if product is None:
            await self._get_existing_product(product_id)
            logger.warning("Insufficient product stock: product_id=%s, quantity=%d", product_id, quantity)
            raise NotEnoughProductError()

        await self._session.commit()
        await self._invalidate_product(product_id)
        logger.info("Product reserved product_id=%s quantity=%s", product_id, quantity)
        return await self._product_read_from_orm(product)

    async def reserve_products(self, items: list[dict]) -> list[ProductRead]:
        """Атомарно зарезервировать все позиции заказа."""
        logger.info("Starting batch product reservation: items=%d", len(items))
        logger.debug("Reservation product IDs: %s", [item.get("product_id") for item in items])
        reserved_products = []
        try:
            for item in items:
                product = await self._product_repo.reserve_product(
                    item["product_id"],
                    item["quantity"],
                )
                if product is None:
                    await self._get_existing_product(item["product_id"])
                    raise NotEnoughProductError()
                reserved_products.append(await self._product_read_from_orm(product))
            await self._session.commit()
        except Exception:
            logger.exception("Batch product reservation failed")
            await self._session.rollback()
            raise
        for product in reserved_products:
            await self._invalidate_product(product.id)
        logger.info("Product batch reserved items_count=%s", len(items))
        return reserved_products

    async def release_product(self, product_id: str, quantity: int) -> None:
        """Освободить товар"""
        logger.info("Releasing product: product_id=%s, quantity=%d", product_id, quantity)
        product = await self._product_repo.release_product(product_id, quantity)
        
        if product is None:
            raise ProductNotFoundError(f"Product {product_id} not found")

        await self._session.commit()
        await self._invalidate_product(product_id)
        logger.info("Product released product_id=%s quantity=%s", product_id, quantity)

    async def release_products(self, items: list[dict]) -> None:
        """Атомарно освободить все позиции заказа."""
        logger.info("Starting batch product release: items=%d", len(items))
        try:
            for item in items:
                product = await self._product_repo.release_product(
                    item["product_id"],
                    item["quantity"],
                )
                if product is None:
                    raise ProductNotFoundError(
                        f"Product {item['product_id']} not found"
                    )
            await self._session.commit()
        except Exception:
            logger.exception("Batch product release failed")
            await self._session.rollback()
            raise
        for item in items:
            await self._invalidate_product(item["product_id"])
        logger.info("Product batch released items_count=%s", len(items))

    async def confirm_products(self, items: list[dict]) -> None:
        """Проверить позиции подтверждаемого резерва без повторного списания."""
        logger.info("Confirming product reservation: items=%d", len(items))
        for item in items:
            if item["quantity"] <= 0:
                logger.warning("Invalid confirmed product quantity: product_id=%s", item.get("product_id"))
                raise ValueError("Confirmed item quantity must be positive")
            await self._get_existing_product(item["product_id"])
        logger.info("Product reservation confirmed: items=%d", len(items))
