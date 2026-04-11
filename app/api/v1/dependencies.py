from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, Dict, List, Optional, Callable

from fastapi import Depends, Request, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.repositories.category_repository import CategoryRepository
# from app.core.repositories.product_repository import ProductRepository
# from app.core.repositories.sku_repository import SkuRepository
from app.core.repositories.user_repository import UserRepository
from app.infrastructure.database.adapters.pg_connection import DatabaseConnection
from app.infrastructure.database.models.user import User, UserRole

security = HTTPBearer()

def _parse_deep_object_filters(query_params: List[tuple[str, str]]) -> Dict[str, Any]:
    """Parse `filters[brand]=Apple&filters[brand]=Samsung` style params into a dict.

    OpenAPI uses deepObject+explode for this; FastAPI doesn't parse it natively.
    """
    parsed: Dict[str, Any] = {}
    for key, value in query_params:
        if not key.startswith("filters[") or not key.endswith("]"):
            continue
        inner_key = key[len("filters[") : -1].strip()
        if not inner_key:
            continue
        if inner_key in parsed:
            if isinstance(parsed[inner_key], list):
                parsed[inner_key].append(value)
            else:
                parsed[inner_key] = [parsed[inner_key], value]
        else:
            parsed[inner_key] = value
    return parsed


async def get_db_connection(request: Request) -> DatabaseConnection:
    return request.app.state.db_connection


async def get_session(
    db: DatabaseConnection = Depends(get_db_connection),
) -> AsyncIterator[AsyncSession]:
    async with db.get_session() as session:
        yield session


async def get_filters_from_query(request: Request) -> Optional[Dict[str, Any]]:
    filters = _parse_deep_object_filters(list(request.query_params.multi_items()))
    return filters or None


# async def get_category_repo(db_connection):
#     session = db_connection.get_session()
#     return CategoryRepository(session)
#
#
# async def get_product_repo(db_connection):
#     session = db_connection.get_session()
#     return ProductRepository(session)
#
#
# async def get_sku_repo(db_connection):
#     session = db_connection.get_session()
#     return SkuRepository(session)

async def get_user_repo(db_session: AsyncSession = Depends(get_session)):
    return UserRepository(db_session)

async def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> uuid:
    user_id = request.state.user_id

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    return user_id

async def get_current_user(
    user_id: uuid = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repo)
) -> User:
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User is inactive"
        )

    return user

def require_role(*roles: List[UserRole]) -> Callable:
    """
    Проверка роли пользователя
    """

    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail="Forbidden"
            )
        return user

    return checker
