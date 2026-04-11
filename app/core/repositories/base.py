from typing import TypeVar, Generic, Optional, List, Type, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update
from sqlalchemy.sql import Select
from app.infrastructure.database.models.base import Base
from uuid import UUID

T = TypeVar("T", bound=Base)


class SqlAlchemyRepository(Generic[T]):
    """Базовый репозиторий с CRUD операциями"""

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: UUID) -> Optional[T]:
        """Получить запись по ID"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[Callable] = None
    ) -> List[T]:
        """Получить все записи с пагинацией"""
        query = select(self.model).offset(offset).limit(limit)
        if order_by:
            query = query.order_by(order_by)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_many(
        self,
        where_clause=None,
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        """Получить записи с фильтром"""
        query = select(self.model)
        if where_clause is not None:
            query = query.where(where_clause)
        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, where_clause=None) -> int:
        """Получить количество записей"""
        query = select(func.count()).select_from(self.model)
        if where_clause is not None:
            query = query.where(where_clause)
        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def create(self, entity: T) -> T:
        """Создать запись"""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        await self.session.commit()
        return entity

    async def update(self, entity: T, **kwargs) -> T:
        """Обновить запись"""
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        await self.session.flush()
        await self.session.refresh(entity)
        await self.session.commit()
        return entity

    async def delete(self, id: UUID) -> bool:
        """Удалить запись по ID"""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def exists(self, id: UUID) -> bool:
        """Проверить существование записи"""
        result = await self.session.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None

    async def get_by_field(self, field: str, value) -> Optional[T]:
        """Получить запись по полю"""
        result = await self.session.execute(
            select(self.model).where(getattr(self.model, field) == value)
        )
        return result.scalar_one_or_none()
