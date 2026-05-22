from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_seller, get_store, hash_password, parse_deep, verify_password
from app.core.store import ServiceError

router = APIRouter()

@router.get("/categories")
async def b2b_categories(request: Request, parent_id: Optional[str] = None, only_root: bool = False):
    store = get_store(request)
    categories = []
    for category in store.categories.values():
        if only_root and category["parent_id"] is not None:
            continue
        if parent_id is not None and category["parent_id"] != parent_id:
            continue
        categories.append(store.category_ref_b2b(category["id"]))
    return categories


@router.post("/categories")
async def b2b_category_create(payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        get_seller(store, authorization)
        category_id = store.new_id()
        category = {
            "id": category_id,
            "name": payload["name"],
            "parent_id": payload.get("parent_id"),
            "is_active": True,
            "created_at": utcnow(),
        }
        store.categories[category_id] = category
        response = store.category_ref_b2b(category_id)
        response["children"] = []
        return JSONResponse(status_code=201, content=jsonable_encoder(response))
    except KeyError:
        return error_response(ServiceError("VALIDATION_ERROR", "Field 'name' is required", 422))
    except ServiceError as exc:
        return error_response(exc)


@router.get("/categories/tree")
async def b2b_categories_tree(request: Request):
    return get_store(request).category_tree_b2b()


@router.get("/categories/{category_id}")
async def b2b_category_get(category_id: str, request: Request):
    store = get_store(request)
    try:
        category = store.categories[category_id]
        response = store.category_ref_b2b(category_id)
        response["children"] = [store.category_ref_b2b(child["id"]) for child in store.categories.values() if child["parent_id"] == category_id]
        return response
    except KeyError:
        return error_response(ServiceError("NOT_FOUND", "Category not found", 404))


@router.patch("/categories/{category_id}")
async def b2b_category_patch(category_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        get_seller(store, authorization)
        category = store.categories[category_id]
        for field in ["name", "parent_id", "is_active"]:
            if field in payload:
                category[field] = payload[field]
        return await b2b_category_get(category_id, request)
    except KeyError:
        return error_response(ServiceError("NOT_FOUND", "Category not found", 404))
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/categories/{category_id}", status_code=204)
async def b2b_category_delete(category_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        get_seller(store, authorization)
        if any(product["category_id"] == category_id for product in store.products.values()):
            raise ServiceError("CONFLICT", "Category has products", 409)
        store.categories.pop(category_id, None)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


@router.get("/categories/{category_id}/breadcrumbs")
async def b2b_category_breadcrumbs(category_id: str, request: Request):
    store = get_store(request)
    try:
        return [store.category_ref_b2b(item_id) for item_id in store.category_path_ids(category_id)]
    except KeyError:
        return error_response(ServiceError("NOT_FOUND", "Category not found", 404))

