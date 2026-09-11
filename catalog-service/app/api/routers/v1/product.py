from fastapi import APIRouter, Depends, File, Header, Query, UploadFile, status

from app.api.dependencies import get_product_service
from app.schemas import ProductCreate, ProductCreateRequest, ProductRead, ProductUpdate
from app.services import ProductService


router = APIRouter(
    prefix="/products",
    tags=["Товары"]
)


@router.get("", response_model=list[ProductRead])
async def get_all_products(
    product_service: ProductService = Depends(get_product_service)
) -> list[ProductRead]:
    return await product_service.get_all_products()


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: str,
    product_service: ProductService = Depends(get_product_service)
) -> ProductRead:
    return await product_service.get_product_by_id(product_id=product_id)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreateRequest,
    seller_id: str = Header(alias="X-User-ID"),
    product_service: ProductService = Depends(get_product_service)
) -> ProductRead:
    return await product_service.create_product(
        product_data=ProductCreate(
            **product_data.model_dump(),
            seller_id=seller_id,
        ),
    )


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: str,
    update_data: ProductUpdate,
    seller_id: str = Header(alias="X-User-ID"),
    product_service: ProductService = Depends(get_product_service)
) -> ProductRead:
    return await product_service.update_product(
        product_id=product_id, 
        seller_id=seller_id,
        update_data=update_data
    )


@router.put("/{product_id}/image", response_model=ProductRead)
async def upload_product_image(
    product_id: str,
    image: UploadFile = File(...),
    seller_id: str = Header(alias="X-User-ID"),
    product_service: ProductService = Depends(get_product_service),
) -> ProductRead:
    content = await image.read(ProductService.MAX_IMAGE_SIZE_BYTES + 1)
    try:
        return await product_service.upload_product_image(
            product_id=product_id,
            seller_id=seller_id,
            content=content,
            content_type=image.content_type or "",
        )
    finally:
        await image.close()


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    seller_id: str = Header(alias="X-User-ID"),
    product_service: ProductService = Depends(get_product_service)
) -> None:
    await product_service.delete_product(product_id=product_id, seller_id=seller_id)


@router.post("/{product_id}/reserve", response_model=ProductRead)
async def reserve_product(
    product_id: str,
    quantity: int = Query(gt=0),
    service: ProductService = Depends(get_product_service),
):
    return await service.reserve_product(product_id, quantity)

@router.post("/{product_id}/release", response_model=dict)
async def release_product(
    product_id: str,
    quantity: int = Query(gt=0),
    service: ProductService = Depends(get_product_service),
):
    await service.release_product(product_id, quantity)
    return {"status": "ok"}
