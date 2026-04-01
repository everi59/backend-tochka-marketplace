from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from uuid import UUID
from app.core.repositories.base import SqlAlchemyRepository
from app.infrastructure.database.models.category import Category


class CategoryRepository(SqlAlchemyRepository[Category]):
    """Репозиторий для работы с категориями"""

    def __init__(self, session):
        super().__init__(session, Category)

    async def get_tree(self) -> List[Category]:
        """Получить дерево категорий (корневые)"""
        result = await self.session.execute(
            select(Category)
            .where(Category.parent_id.is_(None))
            .where(Category.is_active == True)
            .options(joinedload(Category.children))
        )
        return result.scalars().all()

    async def get_by_slug(self, slug: str) -> Optional[Category]:
        """Получить категорию по slug"""
        result = await self.session.execute(
            select(Category).where(Category.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_children(self, parent_id: UUID) -> List[Category]:
        """Получить дочерние категории"""
        result = await self.session.execute(
            select(Category)
            .where(Category.parent_id == parent_id)
            .where(Category.is_active == True)
            .options(joinedload(Category.children))
        )
        return result.scalars().all()

    async def get_ancestors(self, category_id: UUID) -> List[Category]:
        """Получить всех предков категории (для breadcrumbs)"""
        ancestors = []
        current = await self.get_by_id(category_id)

        while current and current.parent_id:
            parent = await self.get_by_id(current.parent_id)
            if parent:
                ancestors.insert(0, parent)
                current = parent
            else:
                break

        return ancestors

    async def get_with_products_count(self) -> List[Category]:
        """Получить категории с количеством товаров"""
        from sqlalchemy import func
        from app.infrastructure.database.models.product import Product

        result = await self.session.execute(
            select(Category)
            .outerjoin(Product, Category.id == Product.category_id)
            .group_by(Category.id)
            .options(joinedload(Category.children))
        )
        return result.scalars().all()