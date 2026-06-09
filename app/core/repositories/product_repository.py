from typing import List, Optional, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload, selectinload
from uuid import UUID
from app.core.repositories.base import SqlAlchemyRepository
from app.infrastructure.database.models.product import Product, ProductStatus
from app.infrastructure.database.models.sku import Sku


class ProductRepository(SqlAlchemyRepository[Product]):
    """Репозиторий для работы с товарами"""

    def __init__(self, session):
        super().__init__(session, Product)

    async def get_products(
            self,
            limit: int = 10,
            offset: int = 0,
            category_id: Optional[UUID] = None,
            search: Optional[str] = None,
            sort: Optional[str] = None,
    ) -> Tuple[List[Product], int]:
        """Получить список товаров с фильтрами и пагинацией"""
        query = select(Product).where(Product.status == ProductStatus.MODERATED)

        if category_id:
            query = query.where(Product.category_id == category_id)

        if search and len(search) >= 3:
            query = query.where(
                or_(
                    Product.title.ilike(f"%{search}%"),
                    Product.description.ilike(f"%{search}%"),
                )
            )

        query = self._apply_sort(query, sort)

        count_query = select(func.count()).select_from(Product).where(
            Product.status == ProductStatus.MODERATED
        )
        if category_id:
            count_query = count_query.where(Product.category_id == category_id)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one() or 0

        query = query.options(
            joinedload(Product.category),
            joinedload(Product.images),
            selectinload(Product.skus),
        ).offset(offset).limit(limit)

        result = await self.session.execute(query)
        products = result.scalars().unique().all()

        return products, total

    def _apply_sort(self, query, sort: Optional[str]):
        if sort == "price_asc":
            query = query.join(Sku).order_by(Sku.price.asc())
        elif sort == "price_desc":
            query = query.join(Sku).order_by(Sku.price.desc())
        elif sort == "date_desc":
            query = query.order_by(Product.created_at.desc())
        else:
            query = query.order_by(Product.created_at.desc())
        return query

    async def get_by_slug(self, slug: str) -> Optional[Product]:
        result = await self.session.execute(
            select(Product)
            .where(Product.slug == slug)
            .options(
                joinedload(Product.category),
                joinedload(Product.images),
                selectinload(Product.skus).joinedload(Sku.characteristics),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_seller_and_slug(self, seller_id: UUID, slug: str) -> Optional[Product]:
        result = await self.session.execute(
            select(Product)
            .where(Product.seller_id == seller_id, Product.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_similar(
            self,
            product_id: UUID,
            category_id: UUID,
            limit: int = 8
    ) -> List[Product]:
        result = await self.session.execute(
            select(Product)
            .where(
                Product.category_id == category_id,
                Product.id != product_id,
                Product.status == ProductStatus.MODERATED,
            )
            .options(joinedload(Product.images))
            .limit(limit)
        )
        return result.scalars().unique().all()

    async def get_skus(self, product_id: UUID) -> List[Sku]:
        result = await self.session.execute(
            select(Sku)
            .where(Sku.product_id == product_id)
            .options(
                joinedload(Sku.images),
                joinedload(Sku.characteristics),
            )
        )
        return result.scalars().all()

    async def get_sku(self, product_id: UUID, sku_id: UUID) -> Optional[Sku]:
        result = await self.session.execute(
            select(Sku)
            .where(Sku.product_id == product_id, Sku.id == sku_id)
            .options(
                joinedload(Sku.images),
                joinedload(Sku.characteristics),
            )
        )
        return result.scalar_one_or_none()
