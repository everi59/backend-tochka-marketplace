from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repositories.category_repository import CategoryRepository
from app.core.repositories.product_repository import ProductRepository
from app.core.repositories.sku_repository import SkuRepository
from app.infrastructure.database.adapters.pg_connection import DatabaseConnection


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


async def get_category_repo(db_connection):
    session = db_connection.get_session()
    return CategoryRepository(session)


async def get_product_repo(db_connection):
    session = db_connection.get_session()
    return ProductRepository(session)


async def get_sku_repo(db_connection):
    session = db_connection.get_session()
    return SkuRepository(session)

