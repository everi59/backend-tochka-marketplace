from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class InvoiceItemCreateDTO(BaseModel):
    sku_id: UUID
    quantity: int = Field(..., ge=1)


class InvoiceCreateDTO(BaseModel):
    """DTO для создания накладной"""
    seller_id: UUID

    items: List[InvoiceItemCreateDTO] = Field(..., min_length=1)

    warehouse_id: Optional[UUID] = None


class InvoiceItemDTO(BaseModel):
    """Позиция накладной в ответе"""
    id: UUID
    sku_id: UUID
    quantity: int
    total: float

    class Config:
        from_attributes = True


class InvoiceDTO(BaseModel):
    """Накладная в ответе"""
    id: UUID
    seller_id: Optional[UUID] = None
    status: str
    total_amount: float
    # total_items: int
    created_at: datetime
    updated_at: datetime
    # accepted_at: Optional[datetime] = None
    items: List[InvoiceItemDTO] = []

    class Config:
        from_attributes = True


class InvoiceListResponseDTO(BaseModel):
    """Ответ со списком накладных"""
    items: List[InvoiceDTO]
    total: int
    limit: int
    offset: int
