from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from uuid import UUID
from typing import Optional, List
from app.core.repositories.invoice_repository import InvoiceRepository
from app.core.repositories.sku_repository import SkuRepository
from app.core.dto.seller.invoice_dto import (
    InvoiceCreateDTO,
    InvoiceDTO,
    InvoiceListResponseDTO,
)
from app.api.v1.dependencies import get_invoice_repo, get_sku_repo, get_invoice_service
from app.core.services.invoice_service import InvoiceService
from app.infrastructure.database.models.invoice import Invoice

router = APIRouter(prefix="/invoices", tags=["Seller: Invoices"])


@router.post("", response_model=InvoiceDTO, status_code=status.HTTP_201_CREATED)
async def create_invoice(
        data: InvoiceCreateDTO = Body(...),
        service: InvoiceService = Depends(get_invoice_service),
):
    """Создать новую накладную"""

    created_invoice = await service.create_invoice(data)

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await service.invoice_repo.session.execute(
        select(Invoice)
        .where(Invoice.id == created_invoice.id)
        .options(selectinload(Invoice.items))
    )
    loaded_invoice = result.scalars().unique().one()

    return loaded_invoice


@router.get("", response_model=InvoiceListResponseDTO)
async def get_invoices(
        seller_id: UUID,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        status_filter: Optional[str] = Query(None),
        repo: InvoiceRepository = Depends(get_invoice_repo),
):
    """
    Получить список накладных продавца с пагинацией.
    """
    invoices, total = await repo.get_by_seller(
        seller_id=seller_id,
        limit=limit,
        offset=offset,
        status=status_filter
    )

    return InvoiceListResponseDTO(
        items=invoices,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{invoice_id}", response_model=InvoiceDTO)
async def get_invoice(
        invoice_id: UUID,
        seller_id: UUID,
        repo: InvoiceRepository = Depends(get_invoice_repo),
):
    """
    Получить детальную информацию о накладной.
    """
    invoice = await repo.get_by_id(invoice_id)
    if not invoice or invoice.seller_id != seller_id:
        raise HTTPException(status_code=404, detail="Накладная не найдена")
    return invoice


@router.put("/{invoice_id}/send", response_model=InvoiceDTO)
async def send_invoice(
        invoice_id: UUID,
        seller_id: UUID,
        repo: InvoiceRepository = Depends(get_invoice_repo),
):
    """
    Отправить накладную на проверку (статус: DRAFT → SENT).
    """
    invoice = await repo.get_by_id(invoice_id)
    if not invoice or invoice.seller_id != seller_id:
        raise HTTPException(status_code=404, detail="Накладная не найдена")

    from app.infrastructure.database.models.invoice import InvoiceStatus
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Можно отправить только черновик",
        )

    updated = await repo.update(invoice, status=InvoiceStatus.SENT)
    return updated
