from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_store
from app.core.store import ServiceError

from .buyers import buyer_id_from_auth

router = APIRouter()


@router.get("/orders")
async def b2c_orders(request: Request, authorization: Optional[str] = Header(None), limit: int = 20, offset: int = 0, status: Optional[str] = None):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        orders = [order for order in store.orders.values() if order["buyer_id"] == buyer_id]
        if status:
            orders = [order for order in orders if order["status"] == status]
        total = len(orders)
        return {"items": store.clone(orders[offset : offset + limit]), "total_count": total, "limit": limit, "offset": offset}
    except ServiceError as exc:
        return error_response(exc)


@router.post("/orders")
async def b2c_create_order(
    payload: dict[str, Any],
    request: Request,
    authorization: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    store = get_store(request)
    try:
        if not idempotency_key:
            raise ServiceError("BAD_REQUEST", "Idempotency-Key is required", 400)
        buyer_id = buyer_id_from_auth(store, authorization)
        order, created = store.create_order(buyer_id, payload, idempotency_key)
        return JSONResponse(status_code=201 if created else 200, content=jsonable_encoder(order))
    except ServiceError as exc:
        if exc.status_code == 422 and exc.details:
            return JSONResponse(status_code=422, content=jsonable_encoder(exc.details))
        return error_response(exc)


@router.get("/orders/{order_id}")
async def b2c_order_get(order_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        order = store.orders.get(order_id)
        if not order or order["buyer_id"] != buyer_id:
            raise ServiceError("NOT_FOUND", "Order not found", 404)
        return store.clone(order)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/orders/{order_id}/cancel")
async def b2c_order_cancel(order_id: str, payload: Optional[dict[str, Any]], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        return await store.cancel_order(request, buyer_id, order_id, (payload or {}).get("reason"))
    except ServiceError as exc:
        return error_response(exc)




