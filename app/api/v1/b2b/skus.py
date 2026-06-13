from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_seller, get_store, hash_password, parse_deep, verify_password
from app.core.store import ServiceError

router = APIRouter()

@router.get("/products/{product_id}/skus")
async def b2b_list_product_skus(product_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        product = store.require_product(product_id)
        store.ensure_seller_owns_product(seller["id"], product)
        return [store.sku_response_b2b(sku_id) for sku_id in product["skus"]]
    except ServiceError as exc:
        return error_response(exc)


@router.post("/skus")
async def b2b_create_sku(payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        sku = store.create_sku(seller["id"], payload)
        return JSONResponse(status_code=201, content=jsonable_encoder(store.sku_response_b2b(sku["id"])))
    except ServiceError as exc:
        return error_response(exc)


@router.get("/skus/{sku_id}")
async def b2b_get_sku(sku_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        sku = store.require_sku(sku_id)
        store.ensure_seller_owns_product(seller["id"], store.require_product(sku["product_id"]))
        return store.sku_response_b2b(sku_id)
    except ServiceError as exc:
        return error_response(exc)


@router.patch("/skus/{sku_id}")
async def b2b_patch_sku(sku_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        store.update_sku(seller["id"], sku_id, payload)
        return store.sku_response_b2b(sku_id)
    except ServiceError as exc:
        return error_response(exc)


@router.put("/skus/{sku_id}")
async def b2b_put_sku(sku_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    return await b2b_patch_sku(sku_id, payload, request, authorization)


@router.delete("/skus/{sku_id}", status_code=204)
async def b2b_delete_sku(sku_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        store.delete_sku(seller["id"], sku_id)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/skus/{sku_id}/images")
async def b2b_add_sku_image(sku_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        sku = store.require_sku(sku_id)
        store.ensure_seller_owns_product(seller["id"], store.require_product(sku["product_id"]))
        image = store._make_image({"image_id": payload.get("image_id"), "url": payload["url"], "ordering": payload.get("ordering", 0)})
        sku["images"].append(image)
        return JSONResponse(status_code=201, content=jsonable_encoder(image))
    except KeyError:
        return error_response(ServiceError("VALIDATION_ERROR", "Field 'url' is required", 422))
    except ServiceError as exc:
        return error_response(exc)


@router.patch("/skus/images/{image_id}")
async def b2b_patch_sku_image(image_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        get_seller(store, authorization)
        for sku in store.skus.values():
            for image in sku["images"]:
                if image["id"] == image_id:
                    if "url" in payload and payload["url"] is not None:
                        image["url"] = payload["url"]
                    if "ordering" in payload and payload["ordering"] is not None:
                        image["ordering"] = int(payload["ordering"])
                    return image
        raise ServiceError("NOT_FOUND", "Image not found", 404)
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/skus/images/{image_id}", status_code=204)
async def b2b_delete_sku_image(image_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        get_seller(store, authorization)
        for sku in store.skus.values():
            sku["images"] = [image for image in sku["images"] if image["id"] != image_id]
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


