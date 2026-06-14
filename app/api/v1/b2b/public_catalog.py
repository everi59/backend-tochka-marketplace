from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_store
from app.core.store import ServiceError

router = APIRouter()

SERVICE_KEY = os.getenv("B2B_SERVICE_KEY", "svc")


def _require_service_key(x_service_key: Optional[str]) -> None:
    if not x_service_key or x_service_key != SERVICE_KEY:
        raise ServiceError("UNAUTHORIZED", "Invalid or missing service key", 401)


@router.get("/public/products")
async def b2b_public_products(
    request: Request,
    x_service_key: Optional[str] = Header(None),
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    seller_id: Optional[str] = None,
    sort: str = "created_desc",
    limit: int = 20,
    offset: int = 0,
):
    store = get_store(request)
    try:
        _require_service_key(x_service_key)
    except ServiceError as exc:
        return error_response(exc)
    filters = {"category_id": category_id, "seller_id": seller_id, "price_min": min_price, "price_max": max_price, "attributes": {}}
    try:
        response = store.list_catalog_products(limit, offset, search, "new" if sort == "created_desc" else sort, filters)
        response["items"] = [_public_product_short(store, item["id"]) for item in response["items"]]
        return response
    except ServiceError as exc:
        return error_response(exc)


@router.post("/public/products/batch")
async def b2b_public_products_batch(payload: dict[str, Any], request: Request, x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        _require_service_key(x_service_key)
    except ServiceError as exc:
        return error_response(exc)
    products = []
    for product_id in payload.get("product_ids", []):
        if product_id in store.public_product_ids():
            products.append(store.product_response_b2b(product_id, public=True))
    return products


@router.get("/public/products/{product_id}")
async def b2b_public_product(product_id: str, request: Request, x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        _require_service_key(x_service_key)
        if product_id not in store.public_product_ids():
            raise ServiceError("NOT_FOUND", "Product not found", 404)
        return store.product_response_b2b(product_id, public=True)
    except ServiceError as exc:
        return error_response(exc)


@router.get("/public/products/{product_id}/similar")
async def b2b_public_similar(product_id: str, request: Request, x_service_key: Optional[str] = Header(None), limit: int = 10):
    store = get_store(request)
    try:
        _require_service_key(x_service_key)
        product = store.require_product(product_id)
        candidates = [pid for pid in store.public_product_ids() if pid != product_id and store.products[pid]["category_id"] == product["category_id"]]
        return [_public_product_short(store, pid) for pid in candidates[:limit]]
    except ServiceError as exc:
        return error_response(exc)


@router.get("/public/skus/{sku_id}")
async def b2b_public_sku(sku_id: str, request: Request, x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        _require_service_key(x_service_key)
        sku = store.require_sku(sku_id)
        product = store.require_product(sku["product_id"])
        if product["status"] != "MODERATED" or product["deleted"]:
            raise ServiceError("NOT_FOUND", "SKU not found", 404)
        return store.sku_response_b2b(sku_id, public=True)
    except ServiceError as exc:
        return error_response(exc)


def _public_product_short(store, product_id: str) -> dict[str, Any]:
    product = store.product_service.require_product(product_id)
    sku_list = [store.skus[sku_id] for sku_id in product["skus"] if sku_id in store.skus]
    prices = [sku["price"] - sku["discount"] for sku in sku_list if store.product_service.active_quantity(sku) > 0]
    min_price = min(prices) if prices else min((sku["price"] - sku["discount"] for sku in sku_list), default=0)
    return {
        "id": product["id"],
        "title": product["title"],
        "slug": product["slug"],
        "status": product["status"],
        "category_id": product["category_id"],
        "created_at": product["created_at"].isoformat().replace("+00:00", "Z"),
        "min_price": min_price,
    }
