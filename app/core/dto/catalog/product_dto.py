from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ProductImageDTO(BaseModel):
    url: str
    order: int

    class Config:
        from_attributes = True


class ProductCharacteristicDTO(BaseModel):
    name: str
    value: str

    class Config:
        from_attributes = True


class ProductBaseDTO(BaseModel):
    slug: str = Field(..., min_length=3, max_length=255)
    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = Field(None, max_length=5000)


class ProductBriefDTO(ProductBaseDTO):
    """Сокращённая версия товара для списков"""
    id: UUID
    title: str
    slug: str
    description: Optional[str] = None
    category_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductDTO(ProductBaseDTO):
    """Полная информация о товаре"""
    id: UUID
    category_id: Optional[UUID] = None
    status: str
    created_at: datetime
    updated_at: datetime
    images: List[ProductImageDTO] = []
    characteristics: List[ProductCharacteristicDTO] = []

    class Config:
        from_attributes = True


class ProductListResponseDTO(BaseModel):
    """Ответ со списком товаров"""
    items: List[ProductBriefDTO]
    total: int
    limit: int
    offset: int


class ProductCreateDTO(BaseModel):
    """DTO для создания товара продавцом"""
    title: str = Field(..., min_length=1, max_length=512)
    slug: str = Field(..., min_length=3, max_length=255, description="URL-идентификатор")
    description: Optional[str] = Field(None, max_length=5000)
    category_id: UUID


class ProductUpdateDTO(BaseModel):
    """DTO для обновления товара продавцом"""
    title: Optional[str] = Field(None, min_length=1, max_length=512)
    slug: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    category_id: Optional[UUID] = None


