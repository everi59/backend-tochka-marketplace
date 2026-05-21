from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import List
from app.core.repositories.category_repository import CategoryRepository
from app.core.repositories.filter_repository import FilterRepository
from app.core.dto.catalog.category_dto import CategoryDTO, CategoryTreeDTO
from app.core.dto.catalog.facet_dto import FacetListResponseDTO
from app.api.v1.dependencies import get_category_repo, get_filter_repo

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("")
async def get_categories(
    repo: CategoryRepository = Depends(get_category_repo),
):
    """Получить дерево категорий"""
    categories = await repo.get_tree()
    return categories


@router.get("/{category_id}", response_model=CategoryDTO)
async def get_category(
    category_id: UUID,
    repo: CategoryRepository = Depends(get_category_repo),
):
    """Получить детальную информацию о категории"""
    category = await repo.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


@router.get("/{category_id}/filters")
async def get_category_filters(
    category_id: UUID,
    repo: FilterRepository = Depends(get_filter_repo),
):
    """Список доступных фильтров для категории"""
    filters = await repo.get_category_filters(category_id)
    return {"filters": filters}
