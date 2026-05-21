from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from uuid import UUID
from app.core.repositories.product_repository import ProductRepository
from app.core.repositories.sku_repository import SkuRepository
from app.core.dto.catalog.product_dto import (
    ProductDTO,
    ProductListResponseDTO,
    ProductBriefDTO,
)
from app.core.dto.catalog.sku_dto import SKUListResponseDTO, SKUDetailDTO
from app.api.v1.dependencies import get_product_repo, get_sku_repo

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=ProductListResponseDTO)
async def get_products(
        limit: int = Query(10, ge=1, le=100, description="Количество товаров"),
        offset: int = Query(0, ge=0, description="Смещение"),
        category_id: Optional[UUID] = Query(None, description="ID категории"),
        search: Optional[str] = Query(None, min_length=3, description="Поисковый запрос"),
        sort: Optional[str] = Query(None, description="Сортировка (price_asc, price_desc, date_desc)"),
        repo: ProductRepository = Depends(get_product_repo),
):
    """Получить список товаров (сокращённая версия) с пагинацией"""
    products, total = await repo.get_products(
        limit=limit,
        offset=offset,
        category_id=category_id,
        search=search,
        sort=sort,
    )
    return ProductListResponseDTO(
        items=products,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{product_id}", response_model=ProductDTO)
async def get_product(
        product_id: UUID,
        repo: ProductRepository = Depends(get_product_repo),
):
    """Получить полный товар"""
    product = await repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product


@router.get("/{product_id}/similar", response_model=List[ProductBriefDTO])
async def get_similar_products(
        product_id: UUID,
        limit: int = Query(8, ge=1, le=50, description="Количество похожих товаров"),
        repo: ProductRepository = Depends(get_product_repo),
):
    """Получить похожие товары"""
    product = await repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    similar = await repo.get_similar(
        product_id=product_id,
        category_id=product.category_id,
        limit=limit,
    )
    return similar


@router.get("/{product_id}/skus", response_model=SKUListResponseDTO)
async def get_product_skus(
        product_id: UUID,
        repo: SkuRepository = Depends(get_sku_repo),
):
    """Получить список SKU товара (кратко - для отображения в карточке)"""
    skus = await repo.get_by_product(product_id)
    return SKUListResponseDTO(items=skus)


@router.get("/{product_id}/skus/{sku_id}", response_model=SKUDetailDTO)
async def get_sku(
        product_id: UUID,
        sku_id: UUID,
        repo: SkuRepository = Depends(get_sku_repo),
):
    """Получить информацию о конкретном SKU"""
    sku = await repo.get_by_id(sku_id)
    if not sku or sku.product_id != product_id:
        raise HTTPException(status_code=404, detail="SKU не найден")
    return sku