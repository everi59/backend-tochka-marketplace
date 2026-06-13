from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_seller, get_store, hash_password, iso, parse_deep, utcnow, verify_password
from app.core.store import ServiceError

router = APIRouter()


@router.get("/sellers/me")
async def b2b_me(request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        return {
            "id": seller["id"],
            "email": seller["email"],
            "first_name": seller["first_name"],
            "last_name": seller["last_name"],
            "middle_name": seller["middle_name"],
            "company_name": seller["company_name"],
            "inn": seller["inn"],
            "phone": seller["phone"],
            "created_at": iso(seller["created_at"]),
            "updated_at": iso(seller["updated_at"]),
        }
    except ServiceError as exc:
        return error_response(exc)


@router.patch("/sellers/me")
async def b2b_me_patch(payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        for field in ["first_name", "last_name", "middle_name", "company_name", "phone"]:
            if field in payload:
                seller[field] = payload[field]
        seller["updated_at"] = utcnow()
        return await b2b_me(request, authorization)
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/sellers/me", status_code=204)
async def b2b_me_delete(request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        seller = get_seller(store, authorization)
        seller["is_active"] = False
        seller["updated_at"] = utcnow()
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)

