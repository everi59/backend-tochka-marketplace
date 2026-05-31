from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dto.seller.invoice_dto import InvoiceItemCreateDTO, InvoiceCreateDTO
from app.core.repositories.sku_repository import SkuRepository
from app.core.repositories.invoice_repository import InvoiceRepository
from app.infrastructure.database.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from fastapi import HTTPException


class InvoiceService:
    """Сервис для бизнес-логики накладных"""

    def __init__(
            self,
            invoice_repo: InvoiceRepository,
            sku_repo: SkuRepository,
    ):
        self.invoice_repo = invoice_repo
        self.sku_repo = sku_repo

    async def calculate_item_total(self, sku_id: UUID, quantity: int) -> tuple[float, float]:
        """
        Рассчитать стоимость позиции накладной.

        Returns:
            tuple: (unit_price, total_amount) — цена за единицу и общая сумма
        """
        sku = await self.sku_repo.get_by_id(sku_id)
        if not sku:
            raise HTTPException(
                status_code=404,
                detail=f"SKU {sku_id} не найден"
            )

        unit_price = sku.price
        total = unit_price * quantity
        return unit_price, total

    async def calculate_invoice_total(self, items: List[InvoiceItemCreateDTO]) -> float:
        """Рассчитать общую сумму накладной"""
        total = 0.0
        for item in items:
            _, item_total = await self.calculate_item_total(item.sku_id, item.quantity)
            total += item_total
        return total

    async def validate_and_prepare_items(
            self,
            items: List[InvoiceItemCreateDTO],
            invoice_id: UUID
    ) -> List[InvoiceItem]:
        """
        Валидировать товары и подготовить объекты InvoiceItem для сохранения.

        Returns:
            List[InvoiceItem]: готовые к добавлению в сессию объекты
        """
        prepared_items = []

        for item_data in items:
            unit_price, total = await self.calculate_item_total(
                item_data.sku_id,
                item_data.quantity
            )

            invoice_item = InvoiceItem(
                invoice_id=invoice_id,
                sku_id=item_data.sku_id,
                quantity=item_data.quantity,
                price=unit_price,  # ← Цена из БД, не от клиента!
                total=total,
            )
            prepared_items.append(invoice_item)

        return prepared_items

    async def create_invoice(self, data: InvoiceCreateDTO) -> Invoice:
        """
        Основная бизнес-логика создания накладной.

        ✅ Валидация товаров
        ✅ Расчёт сумм (цена из БД!)
        ✅ Создание записей
        ✅ Коммит транзакции
        """
        # 1. Считаем общую сумму
        total_amount = await self.calculate_invoice_total(data.items)

        # 2. Создаём накладную
        invoice = Invoice(
            seller_id=data.seller_id,
            status=InvoiceStatus.DRAFT,
            total_amount=total_amount,
            warehouse_id=data.warehouse_id
        )

        created_invoice = await self.invoice_repo.create(invoice)

        # 3. Создаём позиции (с доверенными ценами)
        prepared_items = await self.validate_and_prepare_items(
            data.items,
            created_invoice.id
        )

        for item in prepared_items:
            self.invoice_repo.session.add(item)

        # 4. Коммит
        await self.invoice_repo.session.commit()

        return created_invoice
