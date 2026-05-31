from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_seller, get_store, hash_password, parse_deep, verify_password
from app.core.store import ServiceError

router = APIRouter()

@router.get("/products")
async def b2b_list_products(
    request: Request,
    authorization: Optional[str] = Header(None),
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    include_deleted: bool = False,
):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        return store.list_seller_products(seller["id"], limit, offset, status, include_deleted)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/products")
async def b2b_create_product(payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        product = store.create_product(seller["id"], payload)
        return JSONResponse(status_code=201, content=jsonable_encoder(store.product_response_b2b(product["id"])))
    except ServiceError as exc:
        return error_response(exc)


@router.get("/products/{product_id}")
async def b2b_get_product(product_id: str, request: Request, authorization: Optional[str] = Header(None), x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        public = bool(x_service_key)
        if not public:
            seller = get_seller(store, authorization)
            store.ensure_seller_owns_product(seller["id"], store.require_product(product_id))
        return store.product_response_b2b(product_id, public=public)
    except ServiceError as exc:
        return error_response(exc)


@router.patch("/products/{product_id}")
async def b2b_patch_product(product_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        store.update_product(seller["id"], product_id, payload)
        return store.product_response_b2b(product_id)
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/products/{product_id}", status_code=204)
async def b2b_delete_product(product_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        store.delete_product(seller["id"], product_id)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/products/{product_id}/images")
async def b2b_add_product_image(product_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        product = store.require_product(product_id)
        store.ensure_seller_owns_product(seller["id"], product)
        image = {"image_id": payload.get("image_id"), "url": payload["url"], "ordering": payload.get("ordering", 0)}
        built = store._make_image(image)
        product["images"].append(built)
        return JSONResponse(status_code=201, content=jsonable_encoder(built))
    except KeyError:
        return error_response(ServiceError("VALIDATION_ERROR", "Field 'url' is required", 422))
    except ServiceError as exc:
        return error_response(exc)


@router.patch("/products/images/{image_id}")
async def b2b_patch_product_image(image_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        get_seller(store, authorization)
        for product in store.products.values():
            for image in product["images"]:
                if image["id"] == image_id:
                    if "url" in payload and payload["url"] is not None:
                        image["url"] = payload["url"]
                    if "ordering" in payload and payload["ordering"] is not None:
                        image["ordering"] = int(payload["ordering"])
                    return image
        raise ServiceError("NOT_FOUND", "Image not found", 404)
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/products/images/{image_id}", status_code=204)
async def b2b_delete_product_image(image_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        get_seller(store, authorization)
        for product in store.products.values():
            product["images"] = [image for image in product["images"] if image["id"] != image_id]
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


