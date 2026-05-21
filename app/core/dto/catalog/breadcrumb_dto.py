from pydantic import BaseModel
from typing import List
from uuid import UUID


class BreadcrumbDTO(BaseModel):
    id: UUID
    name: str
    slug: str


class BreadcrumbListResponseDTO(BaseModel):
    breadcrumbs: List[BreadcrumbDTO]