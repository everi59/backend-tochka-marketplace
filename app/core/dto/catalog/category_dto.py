from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class CategoryBaseDTO(BaseModel):
    """Базовые поля категории"""
    name: str = Field(..., min_length=1, max_length=255, description="Название категории")
    slug: str = Field(..., min_length=3, max_length=255, description="URL-идентификатор")
    description: Optional[str] = Field(None, max_length=1000, description="Описание")


class CategoryCreateDTO(CategoryBaseDTO):
    """DTO для создания категории"""
    parent_id: Optional[UUID] = Field(None, description="ID родительской категории")
    is_active: bool = Field(True, description="Активна ли категория")


class CategoryUpdateDTO(BaseModel):
    """DTO для обновления категории"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class CategoryDTO(CategoryBaseDTO):
    """DTO для ответа API"""
    model_config = {"from_attributes": True}

    id: UUID
    parent_id: Optional[UUID] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class CategoryTreeDTO(CategoryDTO):
    """DTO для дерева категорий (с дочерними)"""
    children: List["CategoryTreeDTO"] = []

    class Config:
        from_attributes = True


class CategoryListResponseDTO(BaseModel):
    """DTO для списка категорий"""
    items: List[CategoryDTO]
    total: int


CategoryTreeDTO.model_rebuild()
