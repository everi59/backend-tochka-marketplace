from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_seller, get_store, hash_password, parse_deep, verify_password
from app.core.store import ServiceError

router = APIRouter()

@router.post("/images")
async def b2b_upload_image(
    request: Request,
    authorization: Optional[str] = Header(None),
    file: UploadFile = File(...),
    entity_type: str = "PRODUCT",
    entity_id: Optional[str] = None,
    ordering: int = 0,
):
    store = get_store(request)
    try:
        get_seller(store, authorization)
        image_id = store.new_id()
        image = {
            "id": image_id,
            "url": f"/static/uploads/{image_id}-{file.filename}",
            "ordering": ordering,
            "entity_type": entity_type,
            "entity_id": entity_id,
        }
        store.images[image_id] = image
        return JSONResponse(status_code=201, content=jsonable_encoder(image))
    except ServiceError as exc:
        return error_response(exc)


