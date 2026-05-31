from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, distinct
from sqlalchemy.orm import joinedload
from uuid import UUID

from app.infrastructure.database.models.product import Product, ProductStatus, ProductCharacteristic
from app.infrastructure.database.models.sku import Sku
from app.infrastructure.database.models.category import Category
from app.core.repositories.category_repository import CategoryRepository


class FilterRepository:
    """Репозиторий для работы с фильтрами и фасетами"""

    def __init__(self, session):
        self.session = session

    async def get_facets(self, category_id: UUID) -> List[Dict[str, Any]]:
        """Получить фасеты для категории"""
        facets = []

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

        return facets

    async def get_breadcrumbs(self, category_id: UUID) -> List[Dict[str, Any]]:
        """Получить навигационную цепочку"""
        category_repo = CategoryRepository(self.session)

        ancestors = await category_repo.get_ancestors(category_id)
        current = await category_repo.get_by_id(category_id)

        breadcrumbs = []
        for cat in ancestors:
            breadcrumbs.append({
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
            })

        if current:
            breadcrumbs.append({
                "id": current.id,
                "name": current.name,
                "slug": current.slug,
            })

        return breadcrumbs

    async def get_category_filters(self, category_id: UUID) -> List[Dict[str, Any]]:
        """Получить фильтры для категории из БД"""
        filters = []

        # 1. Фильтр по цене (из SKU)
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
        if price_row[0] is not None and price_row[1] is not None:
            filters.append({
                "type": "price",
                "name": "Цена",
                "min": float(price_row[0]),
                "max": float(price_row[1]),
            })

        # 2. Фильтры по характеристикам товаров (реальные данные из БД)
        characteristics_result = await self.session.execute(
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
            .order_by(ProductCharacteristic.name, ProductCharacteristic.value)
        )

        # Группируем характеристики по имени
        characteristics_dict = {}
        for row in characteristics_result.all():
            if row.name not in characteristics_dict:
                characteristics_dict[row.name] = []
            characteristics_dict[row.name].append({
                "value": row.value,
                "count": row.count,
            })

        # Добавляем каждый тип характеристики как отдельный фильтр
        for char_name, values in characteristics_dict.items():
            filters.append({
                "type": "characteristic",
                "name": char_name,
                "values": values,
            })

        return filters