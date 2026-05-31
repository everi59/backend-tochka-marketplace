from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from uuid import UUID
from app.core.repositories.base import SqlAlchemyRepository
from app.infrastructure.database.models.category import Category


class CategoryRepository(SqlAlchemyRepository[Category]):
    """Репозиторий для работы с категориями"""

    def __init__(self, session):
        super().__init__(session, Category)

    async def get_tree(self) -> List[dict]:
        """
        Получить дерево категорий как список словарей.
        """
        # 1. Загрузите ВСЕ активные категории одним запросом
        result = await self.session.execute(
            select(Category)
            .where(Category.is_active == True)
            .order_by(Category.name)
        )
        all_categories = result.scalars().unique().all()

        # 2. Постройте дерево как словари (рекурсивная функция)
        def build_tree(parent_id: Optional[UUID]) -> List[dict]:
            children = []
            for cat in all_categories:
                if cat.parent_id == parent_id:
                    children.append({
                        "id": str(cat.id),
                        "name": cat.name,
                        "slug": cat.slug,
                        "description": cat.description,
                        "is_active": cat.is_active,
                        "created_at": cat.created_at.isoformat() if cat.created_at else None,
                        "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
                        "children": build_tree(cat.id),  # ← рекурсия
                    })
            return children

        return build_tree(None)

    async def get_by_id(self, category_id: UUID) -> Optional[Category]:
        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalars().unique().one_or_none()

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
