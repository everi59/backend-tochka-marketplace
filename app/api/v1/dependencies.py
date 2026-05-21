from fastapi import Depends, Request
from app.infrastructure.database.adapters.pg_connection import DatabaseConnection
from app.core.repositories.product_repository import ProductRepository
from app.core.repositories.category_repository import CategoryRepository
from app.core.repositories.sku_repository import SkuRepository
from app.core.repositories.filter_repository import FilterRepository
from app.core.services.invoice_service import InvoiceService
from app.core.repositories.invoice_repository import InvoiceRepository


async def get_db_connection(request: Request) -> DatabaseConnection:
    """Получить подключение к БД из app.state"""
    return request.app.state.db_connection


async def get_product_repo(
    db_connection: DatabaseConnection = Depends(get_db_connection)
) -> ProductRepository:
    """Получить репозиторий товаров"""
    session = db_connection.get_session()
    return ProductRepository(session)


async def get_category_repo(
    db_connection: DatabaseConnection = Depends(get_db_connection)
) -> CategoryRepository:
    """Получить репозиторий категорий"""
    session = db_connection.get_session()
    return CategoryRepository(session)


async def get_sku_repo(
    db_connection: DatabaseConnection = Depends(get_db_connection)
) -> SkuRepository:
    """Получить репозиторий SKU"""
    session = db_connection.get_session()
    return SkuRepository(session)


async def get_filter_repo(
    db_connection: DatabaseConnection = Depends(get_db_connection)
) -> FilterRepository:
    """Получить репозиторий фильтров"""
    session = db_connection.get_session()
    return FilterRepository(session)


async def get_invoice_repo(
    db_connection: DatabaseConnection = Depends(get_db_connection)
) -> InvoiceRepository:
    """Получить репозиторий накладных"""
    session = db_connection.get_session()
    return InvoiceRepository(session)


async def get_invoice_service(
    invoice_repo: InvoiceRepository = Depends(get_invoice_repo),
    sku_repo: SkuRepository = Depends(get_sku_repo),
) -> InvoiceService:
    """
    Фабрика для создания экземпляра InvoiceService.
    FastAPI сам подставит репозитории благодаря Depends().
    """
    return InvoiceService(
        invoice_repo=invoice_repo,
        sku_repo=sku_repo
    )
