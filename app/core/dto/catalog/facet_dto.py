from pydantic import BaseModel, Field
from typing import List, Optional


class FacetValueDTO(BaseModel):
    value: str
    count: int


class FacetDTO(BaseModel):
    type: str  # "price", "characteristic"
    name: str
    min: Optional[float] = None  # Для price
    max: Optional[float] = None  # Для price
    values: Optional[List[FacetValueDTO]] = None  # Для characteristic


class FacetListResponseDTO(BaseModel):
    facets: List[FacetDTO]