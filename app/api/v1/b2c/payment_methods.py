from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_store, iso, utcnow
from app.core.store import ServiceError

from .buyers import buyer_id_from_auth

router = APIRouter()


@router.get("/buyers/me/payment-methods")
async def b2c_payment_methods(request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        return store.clone(store.payment_methods.get(buyer_id, []))
    except ServiceError as exc:
        return error_response(exc)


@router.post("/buyers/me/payment-methods")
async def b2c_payment_create(payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        method = store.clone(payload)
        method["id"] = store.new_id()
        method["created_at"] = iso(utcnow())
        store.payment_methods.setdefault(buyer_id, []).append(method)
        return JSONResponse(status_code=201, content=jsonable_encoder(method))
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/buyers/me/payment-methods/{method_id}", status_code=204)
async def b2c_payment_delete(method_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        before = len(store.payment_methods.get(buyer_id, []))
        store.payment_methods[buyer_id] = [item for item in store.payment_methods.get(buyer_id, []) if item["id"] != method_id]
        if len(store.payment_methods.get(buyer_id, [])) == before:
            raise ServiceError("NOT_FOUND", "Payment method not found", 404)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)




