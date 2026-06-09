from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_buyer, get_store, hash_password, iso, parse_deep, require_service_key, utcnow, verify_password
from app.core.store import NeoMarketStore, ServiceError

router = APIRouter()

@router.post("/b2b/events", status_code=202)
async def b2c_b2b_events(payload: dict[str, Any], request: Request, x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        require_service_key(x_service_key)
        store.handle_b2b_event(payload)
        return Response(status_code=202)
    except ServiceError as exc:
        return error_response(exc)


