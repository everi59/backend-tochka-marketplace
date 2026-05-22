from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_seller, get_store, hash_password, parse_deep, verify_password
from app.core.store import ServiceError

router = APIRouter()

@router.post("/moderation/events", status_code=204)
async def b2b_moderation_events(payload: dict[str, Any], request: Request, x_service_key: str = Header(...)):
    store = get_store(request)
    try:
        store.handle_moderation_event(payload)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)


