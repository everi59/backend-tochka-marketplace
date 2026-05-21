from typing import List, Optional, Tuple, Sequence, Any
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import selectinload
from uuid import UUID
from app.core.repositories.base import SqlAlchemyRepository
from app.infrastructure.database.models import Invoice
from app.infrastructure.database.models.invoice import Invoice, InvoiceStatus, InvoiceItem


class InvoiceRepository(SqlAlchemyRepository[Invoice]):
    """Репозиторий для работы с накладными"""

    def __init__(self, session):
        super().__init__(session, Invoice)

    async def get_by_seller(
            self,
            seller_id: UUID,
            limit: int = 20,
            offset: int = 0,
            status: Optional[str] = None,
    ) -> tuple[Sequence[Invoice], int | Any]:
        """Получить накладные продавца с фильтрами"""
        query = select(Invoice).where(Invoice.seller_id == seller_id)

        if status:
            try:
                status_enum = InvoiceStatus(status)
                query = query.where(Invoice.status == status_enum)
            except ValueError:
                pass

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        query = query.options(selectinload(Invoice.items))

        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)

        invoices = result.scalars().unique().all()

        return list(invoices), total

    async def create_with_items(self, invoice: Invoice, items_: List[dict]) -> Invoice:
        """Создать накладную с позициями"""
        # Создаём накладную
        created = await self.create(invoice)

        # Добавляем позиции
        for item_data in items_:
            item = InvoiceItem(
                invoice_id=created.id,
                sku_id=item_data["sku_id"],
                quantity=item_data["quantity"],
                price=item_data["price"],
                total=item_data["quantity"] * item_data["price"],
            )
            self.session.add(item)

        await self.session.flush()
        await self.session.refresh(created)

        return created

    async def get_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .options(selectinload(Invoice.items))
        )
        return result.scalars().unique().one_or_none()
