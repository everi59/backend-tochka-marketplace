from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_buyer, get_store, hash_password, iso, parse_deep, utcnow, verify_password
from app.core.store import NeoMarketStore, ServiceError

router = APIRouter()


@router.get("/catalog/categories")
async def b2c_catalog_categories(request: Request):
    store = get_store(request)
    return [store.category_ref(category["id"]) for category in store.categories.values()]


@router.get("/catalog/categories/tree")
async def b2c_catalog_categories_tree(request: Request):
    return get_store(request).category_tree_b2c()


@router.get("/catalog/products")
async def b2c_catalog_products(request: Request, limit: int = 20, offset: int = 0, q: Optional[str] = None, sort: str = "popularity"):
    store = get_store(request)
    filter_data = parse_deep("filter", list(request.query_params.multi_items()))
    mapped_sort = {"popularity": "price_asc", "new": "new", "price_asc": "price_asc", "price_desc": "price_desc"}.get(sort)
    try:
        if mapped_sort is None:
            raise ServiceError("BAD_REQUEST", "Invalid sort value. Allowed values: popularity, new, price_asc, price_desc", 400)
        return store.list_catalog_products(limit, offset, q, mapped_sort, filter_data)
    except ServiceError as exc:
        return error_response(exc)


@router.get("/catalog/facets")
async def b2c_catalog_facets(category_id: str, request: Request):
    store = get_store(request)
    try:
        return store.catalog_facets(category_id)
    except ServiceError as exc:
        return error_response(exc)


@router.get("/catalog/products/{product_id}")
async def b2c_catalog_product(product_id: str, request: Request):
    store = get_store(request)
    try:
        if product_id not in store.public_product_ids():
            raise ServiceError("NOT_FOUND", "Product not found", 404)
        return store.catalog_product_detail(product_id)
    except ServiceError as exc:
        return error_response(exc)


@router.get("/catalog/products/{product_id}/similar")
async def b2c_catalog_similar(product_id: str, request: Request, limit: int = 10):
    store = get_store(request)
    try:
        product = store.require_product(product_id)
        candidates = [pid for pid in store.public_product_ids() if pid != product_id and store.products[pid]["category_id"] == product["category_id"]]
        return [store.catalog_product_card(pid) for pid in candidates[:limit]]
    except ServiceError as exc:
        return error_response(exc)


@router.get("/catalog/banners")
async def b2c_banners(request: Request):
    return get_store(request).clone(get_store(request).banners)


@router.get("/catalog/collections")
async def b2c_collections(request: Request):
    return get_store(request).clone(get_store(request).collections)



