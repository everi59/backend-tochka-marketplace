from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, distinct
from sqlalchemy.orm import joinedload
from uuid import UUID
from app.core.repositories.base import SqlAlchemyRepository
from app.infrastructure.database.models.product import Product, ProductStatus
from app.infrastructure.database.models.sku import Sku
from app.infrastructure.database.models.product import ProductCharacteristic
from app.infrastructure.database.models.sku import SkuCharacteristic


class FilterRepository:
    """Репозиторий для работы с фильтрами и фасетами"""

    def __init__(self, session):
        self.session = session

    async def get_facets(
            self,
            category_id: UUID,
            filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Получить фасеты для категории"""
        facets = []

        # Фасет по цене
        price_result = await self.session.execute(
            select(func.min(Sku.price), func.max(Sku.price))
            .select_from(Sku)
            .join(Product, Sku.product_id == Product.id)
            .where(
                Product.category_id == category_id,
                Product.status == ProductStatus.MODERATED,
            )
        )
        price_row = price_result.one()
        facets.append({
            "type": "price",
            "name": "Цена",
            "min": price_row[0] or 0,
            "max": price_row[1] or 0,
        })

        # Фасет по характеристикам товаров
        char_result = await self.session.execute(
            select(
                ProductCharacteristic.name,
                ProductCharacteristic.value,
                func.count().label("count")
            )
            .join(Product, ProductCharacteristic.product_id == Product.id)
            .where(
                Product.category_id == category_id,
                Product.status == ProductStatus.MODERATED,
            )
            .group_by(ProductCharacteristic.name, ProductCharacteristic.value)
        )

        characteristics = {}
        for row in char_result.all():
            if row.name not in characteristics:
                characteristics[row.name] = []
            characteristics[row.name].append({
                "value": row.value,
                "count": row.count,
            })

        for name, values in characteristics.items():
            facets.append({
                "type": "characteristic",
                "name": name,
                "values": values,
            })

        return facets
