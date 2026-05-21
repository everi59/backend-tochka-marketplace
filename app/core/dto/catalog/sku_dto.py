from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class SKUImageDTO(BaseModel):
    url: str
    order: int

    class Config:
        from_attributes = True


class SKUCharacteristicDTO(BaseModel):
    name: str
    value: str

    class Config:
        from_attributes = True


class SKUBriefDTO(BaseModel):
    """Краткая информация о SKU для списка"""
    id: UUID
    product_id: UUID
    name: str
    price: float
    quantity: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SKUDetailDTO(BaseModel):
    """Полная информация о SKU"""
    id: UUID
    name: str
    price: float
    quantity: int
    characteristics: List[SKUCharacteristicDTO] = []
    images: List[SKUImageDTO] = []

    class Config:
        from_attributes = True


class SKUListResponseDTO(BaseModel):
    """Ответ со списком SKU"""
    items: List[SKUBriefDTO]


class SKUCreateDTO(BaseModel):
    """DTO для создания SKU"""
    name: str = Field(..., min_length=1, max_length=512)
    price: float = Field(..., ge=0)
    quantity: int = Field(..., ge=0)
    characteristics: Optional[List[dict]] = None
    images: Optional[List[dict]] = None


class SKUUpdateDTO(BaseModel):
    """DTO для обновления SKU"""
    name: Optional[str] = Field(None, min_length=1, max_length=512)
    price: Optional[float] = Field(None, ge=0)
    quantity: Optional[int] = Field(None, ge=0)
