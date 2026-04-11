from typing import Optional, List
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from app.core.repositories.base import SqlAlchemyRepository
from app.infrastructure.database.models.user import User, UserRole


class UserRepository(SqlAlchemyRepository[User]):
    """Репозиторий для работы с пользователями"""

    def __init__(self, session):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Получить пользователя по email"""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_nickname(self, nickname: str) -> Optional[User]:
        """Получить пользователя по nickname"""
        result = await self.session.execute(
            select(User).where(User.nickname == nickname)
        )
        return result.scalar_one_or_none()

    async def get_active_users(self) -> List[User]:
        """Получить всех активных пользователей"""
        result = await self.session.execute(
            select(User).where(User.is_active == True)
        )
        return result.scalars().all()

    async def get_verified_users(self) -> List[User]:
        """Получить подтвержденных пользователей"""
        result = await self.session.execute(
            select(User).where(User.is_verified == True)
        )
        return result.scalars().all()

    async def search_by_nickname(self, query: str) -> List[User]:
        """Поиск пользователей по nickname"""
        result = await self.session.execute(
            select(User).where(User.nickname.ilike(f"%{query}%"))
        )
        return result.scalars().all()

    async def activate_user(self, user_id: UUID) -> None:
        """Активировать пользователя"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=True, updated_at=datetime.utcnow())
        )
        await self.session.commit()

    async def deactivate_user(self, user_id: UUID) -> None:
        """Деактивировать пользователя"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        await self.session.commit()

    async def verify_user(self, user_id: UUID) -> None:
        """Подтвердить пользователя"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_verified=True, updated_at=datetime.utcnow())
        )
        await self.session.commit()

    async def update_last_login(self, user_id: UUID) -> None:
        """Обновить время последнего входа"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(updated_at=datetime.utcnow())
        )
        await self.session.commit()

    async def get_recent_users(self, limit: int = 10) -> List[User]:
        """Получить последних зарегистрированных пользователей"""
        result = await self.session.execute(
            select(User)
            .order_by(User.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_admins(self) -> List[User]:
        result = await self.session.execute(
            select(User).where(User.role == UserRole.ADMIN)
        )
        return result.scalars().all()

    async def set_role(self, user_id: UUID, role: UserRole) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(role=role)
        )
        await self.session.commit()