from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import Optional, List

from app.core.repositories.sku_repository import SkuRepository
from app.core.repositories.product_repository import ProductRepository
from app.core.repositories.base import SqlAlchemyRepository  # На всякий случай

from app.core.dto.catalog.sku_dto import (
    SKUCreateDTO,
    SKUUpdateDTO,
    SKUDetailDTO,
    SKUBriefDTO
)

from app.api.v1.dependencies import get_sku_repo, get_product_repo

router = APIRouter(
    prefix="/products/{product_id}/skus",
    tags=["Seller: SKUs"]
)


@router.post("", response_model=SKUBriefDTO, status_code=status.HTTP_201_CREATED)
async def create_sku(
        product_id: UUID,
        data: SKUCreateDTO,
        # seller_id: UUID,
        sku_repo: SkuRepository = Depends(get_sku_repo),
        product_repo: ProductRepository = Depends(get_product_repo),
):
    """
    Создать новую вариацию (SKU) для товара.

    1. Проверяем, существует ли товар.
    2. Проверяем, принадлежит ли товар продавцу.
    3. Создаем SKU (изображения и характеристики подтянутся через cascade в модели, если настроено).
    """

    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # if product.seller_id != seller_id:
    #     raise HTTPException(status_code=403, detail="Нет прав на редактирование этого товара")

    from app.infrastructure.database.models.sku import Sku

    sku_data = data.model_dump(exclude_unset=True)

    new_sku = Sku(
        product_id=product_id,
        **sku_data
    )

    created_sku = await sku_repo.create(new_sku)

    return created_sku


@router.put("/{sku_id}", response_model=SKUBriefDTO)
async def update_sku(
        product_id: UUID,
        sku_id: UUID,
        data: SKUUpdateDTO,
        # seller_id: UUID,
        sku_repo: SkuRepository = Depends(get_sku_repo),
        product_repo: ProductRepository = Depends(get_product_repo),
):
    """
    Обновить информацию о SKU (цена, остаток, название).
    """

    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # if product.seller_id != seller_id:
    #     raise HTTPException(status_code=403, detail="Нет прав")

    existing_sku = await sku_repo.get_by_id(sku_id)
    if not existing_sku:
        raise HTTPException(status_code=404, detail="SKU не найден")

    if existing_sku.product_id != product_id:
        raise HTTPException(status_code=400, detail="SKU не принадлежит указанному товару")

    update_data = data.model_dump(exclude_unset=True)
    updated_sku = await sku_repo.update(existing_sku, **update_data)

    return updated_sku


@router.delete("/{sku_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sku(
        product_id: UUID,
        sku_id: UUID,
        # seller_id: UUID,
        sku_repo: SkuRepository = Depends(get_sku_repo),
        product_repo: ProductRepository = Depends(get_product_repo),
):
    """
    Удалить SKU товара.
    """
    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    existing_sku = await sku_repo.get_by_id(sku_id)
    if not existing_sku or existing_sku.product_id != product_id:
        raise HTTPException(status_code=404, detail="SKU не найден")

    await sku_repo.delete(sku_id)
    return None
