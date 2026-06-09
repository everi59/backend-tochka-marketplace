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

@router.get("/favorites")
async def b2c_favorites(request: Request, authorization: Optional[str] = Header(None), limit: int = 20, offset: int = 0):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        cards = [
            store.catalog_product_card(product_id)
            for product_id in store.favorites.get(buyer_id, set())
            if product_id in store.public_product_ids()
        ]
        total = len(cards)
        return {"items": cards[offset : offset + limit], "total_count": total, "limit": limit, "offset": offset}
    except ServiceError as exc:
        return error_response(exc)


@router.put("/favorites/{product_id}", status_code=204)
async def b2c_favorite_add(product_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        store.add_favorite(buyer_id, product_id)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/favorites/{product_id}", status_code=204)
async def b2c_favorite_delete(product_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        store.remove_favorite(buyer_id, product_id)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/favorites/{product_id}/subscribe", status_code=204)
async def b2c_subscribe(product_id: str, payload: Optional[dict[str, Any]], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        events = (payload or {}).get("events") or ["BACK_IN_STOCK", "PRICE_DROP"]
        store.subscribe_product(buyer_id, product_id, events)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/favorites/{product_id}/subscribe", status_code=204)
async def b2c_unsubscribe(product_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        store.unsubscribe_product(buyer_id, product_id)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)




