from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Form, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_seller, get_store, hash_password, parse_deep, verify_password
from app.core.store import ServiceError

router = APIRouter()

MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_MAGIC = {
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
    "image/webp": (b"RIFF", ".webp"),
}


def _check_image_owner(store: Any, seller_id: str, entity_type: str, entity_id: str) -> None:
    if entity_type == "product":
        product = store.require_product(entity_id)
        store.ensure_seller_owns_product(seller_id, product)
        return
    if entity_type == "sku":
        sku = store.require_sku(entity_id)
        product = store.require_product(sku["product_id"])
        store.ensure_seller_owns_product(seller_id, product)
        return
    raise ServiceError("INVALID_REQUEST", "entity_type must be 'product' or 'sku'", 400)


def _attach_image(store: Any, image: dict[str, Any]) -> None:
    if image["entity_type"] == "product":
        store.products[image["entity_id"]]["images"].append({"id": image["id"], "url": image["url"], "alt": "", "ordering": image["ordering"], "is_main": image["ordering"] == 0})
    else:
        store.skus[image["entity_id"]]["images"].append({"id": image["id"], "url": image["url"], "alt": "", "ordering": image["ordering"], "is_main": image["ordering"] == 0})

@router.post("/images")
async def b2b_upload_image(
    request: Request,
    authorization: Optional[str] = Header(None),
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    ordering: int = Form(...),
):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        normalized_type = entity_type.lower()
        if entity_id is None:
            raise ServiceError("NOT_FOUND", "Entity not found", 404)
        if ordering < 0:
            raise ServiceError("INVALID_REQUEST", "ordering must be >= 0", 400)
        _check_image_owner(store, seller["id"], normalized_type, entity_id)

        content = await file.read()
        if len(content) > MAX_IMAGE_SIZE:
            raise ServiceError("FILE_TOO_LARGE", "Maximum file size is 5 MB", 413)
        expected = ALLOWED_MAGIC.get(file.content_type or "")
        if expected is None:
            raise ServiceError("UNSUPPORTED_MEDIA_TYPE", "Only JPEG, PNG and WebP are supported", 415)
        magic, ext = expected
        if not content.startswith(magic) or (file.content_type == "image/webp" and content[8:12] != b"WEBP"):
            raise ServiceError("INVALID_IMAGE", "File is not a valid image", 400)

        image_id = store.new_id()
        image = {
            "id": image_id,
            "url": f"/media/products/{entity_id}/{image_id}{ext}",
            "ordering": ordering,
            "entity_type": normalized_type,
            "entity_id": entity_id,
        }
        store.images[image_id] = image
        _attach_image(store, image)
        return JSONResponse(status_code=201, content=jsonable_encoder(image))
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/images/{image_id}")
async def b2b_delete_image(image_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        image = store.images.get(image_id)
        if not image:
            raise ServiceError("NOT_FOUND", "Image not found", 404)
        _check_image_owner(store, seller["id"], image["entity_type"], image["entity_id"])
        if image["entity_type"] == "product":
            store.products[image["entity_id"]]["images"] = [item for item in store.products[image["entity_id"]]["images"] if item["id"] != image_id]
        else:
            store.skus[image["entity_id"]]["images"] = [item for item in store.skus[image["entity_id"]]["images"] if item["id"] != image_id]
        del store.images[image_id]
        return {"ok": True}
    except ServiceError as exc:
        return error_response(exc)

