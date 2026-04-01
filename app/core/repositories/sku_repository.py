from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from uuid import UUID
from app.core.repositories.base import SqlAlchemyRepository
from app.infrastructure.database.models.sku import Sku


class SkuRepository(SqlAlchemyRepository[Sku]):
    """Репозиторий для работы с SKU"""

    def __init__(self, session):
        super().__init__(session, Sku)

    async def get_by_product(self, product_id: UUID) -> List[Sku]:
        """Получить все SKU товара"""
        result = await self.session.execute(
            select(Sku)
            .where(Sku.product_id == product_id)
            .options(
                joinedload(Sku.images),
                joinedload(Sku.characteristics),
            )
        )
        return result.scalars().all()

    async def get_available(self, product_id: UUID) -> List[Sku]:
        """Получить только доступные SKU (в наличии)"""
        result = await self.session.execute(
            select(Sku)
            .where(Sku.product_id == product_id, Sku.quantity > 0)
            .options(joinedload(Sku.images))
        )
        return result.scalars().all()

    async def get_min_price(self, product_id: UUID) -> Optional[float]:
        """Получить минимальную цену среди SKU"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.min(Sku.price)).where(Sku.product_id == product_id)
        )
        return result.scalar_one_or_none()

    async def get_in_stock_count(self, product_id: UUID) -> int:
        """Получить количество SKU в наличии"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count()).where(
                Sku.product_id == product_id,
                Sku.quantity > 0
            )
        )
        return result.scalar_one() or 0
