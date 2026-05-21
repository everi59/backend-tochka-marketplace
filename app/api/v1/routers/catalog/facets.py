from fastapi import APIRouter, Depends, Query
from uuid import UUID
from app.core.repositories.filter_repository import FilterRepository
from app.core.dto.catalog.facet_dto import FacetListResponseDTO
from app.core.dto.catalog.breadcrumb_dto import BreadcrumbListResponseDTO
from app.api.v1.dependencies import get_filter_repo

router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("/facets", response_model=FacetListResponseDTO)
async def get_facets(
    category_id: UUID = Query(..., description="ID категории"),
    repo: FilterRepository = Depends(get_filter_repo),
):
    """Список фасетов (фильтров) для категории с подсчётом значений"""
    facets = await repo.get_facets(category_id)
    return FacetListResponseDTO(facets=facets)


@router.get("/breadcrumbs", response_model=BreadcrumbListResponseDTO)
async def get_breadcrumbs(
    category_id: UUID = Query(..., description="ID категории"),
    repo: FilterRepository = Depends(get_filter_repo),
):
    """Построение навигационной цепочки"""
    breadcrumbs = await repo.get_breadcrumbs(category_id)
    return BreadcrumbListResponseDTO(breadcrumbs=breadcrumbs)