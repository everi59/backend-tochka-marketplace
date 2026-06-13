from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_seller, get_store, hash_password, parse_deep, verify_password
from app.core.store import ServiceError

router = APIRouter()

@router.get("/invoices")
async def b2b_list_invoices(request: Request, authorization: Optional[str] = Header(None), limit: int = 20, offset: int = 0, status: Optional[str] = None):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        invoices = [invoice for invoice in store.invoices.values() if invoice["seller_id"] == seller["id"]]
        if status:
            invoices = [invoice for invoice in invoices if invoice["status"] == status]
        total = len(invoices)
        slice_ = invoices[offset : offset + limit]
        return {"items": [store.clone(item) for item in slice_], "total_count": total, "limit": limit, "offset": offset}
    except ServiceError as exc:
        return error_response(exc)


@router.post("/invoices")
async def b2b_create_invoice(payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        invoice = store.create_invoice(seller["id"], payload.get("items", []))
        return JSONResponse(status_code=201, content=jsonable_encoder(invoice))
    except ServiceError as exc:
        return error_response(exc)


@router.get("/invoices/{invoice_id}")
async def b2b_get_invoice(invoice_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        invoice = store.invoices.get(invoice_id)
        if not invoice or invoice["seller_id"] != seller["id"]:
            raise ServiceError("NOT_FOUND", "Invoice not found", 404)
        return store.clone(invoice)
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/invoices/{invoice_id}", status_code=204)
async def b2b_delete_invoice(invoice_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        invoice = store.invoices.get(invoice_id)
        if not invoice or invoice["seller_id"] != seller["id"]:
            raise ServiceError("NOT_FOUND", "Invoice not found", 404)
        if invoice["status"] != "CREATED":
            raise ServiceError("CONFLICT", "Invoice cannot be deleted", 409)
        del store.invoices[invoice_id]
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/invoices/{invoice_id}/accept")
async def b2b_accept_invoice(invoice_id: str, payload: Optional[dict[str, Any]], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        get_seller(store, authorization)
        body = payload or {}
        invoice = store.accept_invoice(invoice_id, body.get("accepted_items") or body.get("items"))
        return invoice
    except ServiceError as exc:
        return error_response(exc)


