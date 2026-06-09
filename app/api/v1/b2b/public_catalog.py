from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_seller, get_store, hash_password, parse_deep, require_service_key, verify_password
from app.core.store import ServiceError

router = APIRouter()


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
        require_service_key(x_service_key)
    except ServiceError as exc:
        return error_response(exc)
    filters = {"category_id": category_id, "seller_id": seller_id, "price_min": min_price, "price_max": max_price, "attributes": {}}
    try:
        response = store.list_catalog_products(limit, offset, search, "new" if sort == "created_desc" else sort, filters)
        response["items"] = [store.public_product_short(item["id"]) for item in response["items"]]
        return response
    except ServiceError as exc:
        return error_response(exc)


@router.post("/public/products/batch")
async def b2b_public_products_batch(payload: dict[str, Any], request: Request, x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        require_service_key(x_service_key)
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
        require_service_key(x_service_key)
        if product_id not in store.public_product_ids():
            raise ServiceError("NOT_FOUND", "Product not found", 404)
        return store.product_response_b2b(product_id, public=True)
    except ServiceError as exc:
        return error_response(exc)


@router.get("/public/products/{product_id}/similar")
async def b2b_public_similar(product_id: str, request: Request, x_service_key: Optional[str] = Header(None), limit: int = 10):
    store = get_store(request)
    try:
        require_service_key(x_service_key)
        product = store.require_product(product_id)
        candidates = [pid for pid in store.public_product_ids() if pid != product_id and store.products[pid]["category_id"] == product["category_id"]]
        return [store.catalog_product_card(pid) for pid in candidates[:limit]]
    except ServiceError as exc:
        return error_response(exc)


@router.get("/public/skus/{sku_id}")
async def b2b_public_sku(sku_id: str, request: Request, x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        require_service_key(x_service_key)
        sku = store.require_sku(sku_id)
        product = store.require_product(sku["product_id"])
        if product["status"] != "MODERATED" or product["deleted"]:
            raise ServiceError("NOT_FOUND", "SKU not found", 404)
        return store.sku_response_b2b(sku_id, public=True)
    except ServiceError as exc:
        return error_response(exc)


