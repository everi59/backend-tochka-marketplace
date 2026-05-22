from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_buyer, get_store, hash_password, iso, parse_deep, utcnow, verify_password
from app.core.store import NeoMarketStore, ServiceError

router = APIRouter()

@router.get("/cart")
async def b2c_get_cart(request: Request, authorization: Optional[str] = Header(None), x_session_id: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = get_buyer(store, authorization)["id"] if authorization else None
        return store.build_cart_response(buyer_id, x_session_id)
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/cart", status_code=204)
async def b2c_clear_cart(request: Request, authorization: Optional[str] = Header(None), x_session_id: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = get_buyer(store, authorization)["id"] if authorization else None
        store.clear_cart(buyer_id, x_session_id)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/cart/items")
async def b2c_add_cart_item(payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None), x_session_id: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = get_buyer(store, authorization)["id"] if authorization else None
        return store.add_cart_item(buyer_id, x_session_id, payload["sku_id"], int(payload["quantity"]))
    except KeyError as exc:
        return error_response(ServiceError("VALIDATION_ERROR", f"Missing field {exc}", 400))
    except ServiceError as exc:
        return error_response(exc)


@router.patch("/cart/items/{sku_id}")
async def b2c_patch_cart_item(sku_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None), x_session_id: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = get_buyer(store, authorization)["id"] if authorization else None
        return store.patch_cart_item(buyer_id, x_session_id, sku_id, int(payload["quantity"]))
    except KeyError:
        return error_response(ServiceError("VALIDATION_ERROR", "Field 'quantity' is required", 400))
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/cart/items/{sku_id}")
async def b2c_delete_cart_item(sku_id: str, request: Request, authorization: Optional[str] = Header(None), x_session_id: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = get_buyer(store, authorization)["id"] if authorization else None
        return store.remove_cart_item(buyer_id, x_session_id, sku_id)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/cart/validate")
async def b2c_validate_cart(request: Request, authorization: Optional[str] = Header(None), x_session_id: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = get_buyer(store, authorization)["id"] if authorization else None
        return store.validate_cart(buyer_id, x_session_id)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/cart/merge")
async def b2c_merge_cart(request: Request, authorization: Optional[str] = Header(None), x_session_id: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        if not x_session_id:
            raise ServiceError("BAD_REQUEST", "X-Session-Id is required", 400)
        buyer = get_buyer(store, authorization)
        return store.merge_cart(buyer["id"], x_session_id)
    except ServiceError as exc:
        return error_response(exc)



