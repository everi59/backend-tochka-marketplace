from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.repositories.product_repository import ProductRepository
from app.core.dto.catalog.product_dto import (
    ProductCreateDTO,
    ProductUpdateDTO,
    ProductDTO,
    ProductBriefDTO
)
from app.api.v1.dependencies    import get_product_repo

router = APIRouter(prefix="/products", tags=["Seller: Products"])


@router.post("", response_model=ProductBriefDTO, status_code=status.HTTP_201_CREATED)
async def create_product(
        data: ProductCreateDTO,
        # seller_id: UUID,
        repo: ProductRepository = Depends(get_product_repo),
):
    """
    Создать новый товар продавца.

    Статус по умолчанию: CREATED (ожидает модерации)
    """
    from app.infrastructure.database.models.product import Product, ProductStatus

    product = Product(
        **data.model_dump(),
        status=ProductStatus.ON_MODERATED,
    )

    created = await repo.create(product)

    result = await repo.session.execute(
        select(Product)
        .where(Product.id == created.id)
        .options(
            selectinload(Product.images),
            selectinload(Product.characteristics),
        )
    )

    loaded_product = result.scalars().unique().one()

    return loaded_product


@router.put("/{product_id}", response_model=ProductBriefDTO)
async def update_product(
        product_id: UUID,
        data: ProductUpdateDTO,
        # seller_id: UUID,
        repo: ProductRepository = Depends(get_product_repo),
):
    """
    Обновить товар продавца.

    При изменении важных полей товар уходит на повторную модерацию.
    """
    product = await repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    critical_fields = {"title", "description", "category_id"}
    if any(getattr(data, field, None) is not None for field in critical_fields):
        from app.infrastructure.database.models.product import ProductStatus
        data_dict = data.model_dump(exclude_unset=True)
        data_dict["status"] = ProductStatus.ON_MODERATED
        updated = await repo.update(product, **data_dict)
    else:
        updated = await repo.update(product, **data.model_dump(exclude_unset=True))

    return updated

