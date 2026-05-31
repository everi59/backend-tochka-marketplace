from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Header, Request, Response

from app.api.v1.common import error_response, get_buyer, get_store, iso, utcnow
from app.core.store import NeoMarketStore, ServiceError

router = APIRouter()


def buyer_id_from_auth(store: NeoMarketStore, authorization: Optional[str]) -> str:
    return get_buyer(store, authorization)["id"]


@router.get("/buyers/me")
async def b2c_buyer_me(request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer = get_buyer(store, authorization)
        return {
            "id": buyer["id"],
            "email": buyer["email"],
            "first_name": buyer["first_name"],
            "last_name": buyer["last_name"],
            "phone": buyer["phone"],
            "date_of_birth": buyer["date_of_birth"].isoformat() if isinstance(buyer["date_of_birth"], date) else None,
            "is_active": buyer["is_active"],
            "created_at": iso(buyer["created_at"]),
            "updated_at": iso(buyer["updated_at"]),
        }
    except ServiceError as exc:
        return error_response(exc)


@router.patch("/buyers/me")
async def b2c_buyer_patch(payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer = get_buyer(store, authorization)
        for field in ["first_name", "last_name", "phone"]:
            if field in payload:
                buyer[field] = payload[field]
        if "date_of_birth" in payload and payload["date_of_birth"]:
            buyer["date_of_birth"] = date.fromisoformat(payload["date_of_birth"])
        buyer["updated_at"] = utcnow()
        return await b2c_buyer_me(request, authorization)
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/buyers/me", status_code=204)
async def b2c_buyer_delete(request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer = get_buyer(store, authorization)
        buyer["is_active"] = False
        buyer["updated_at"] = utcnow()
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)
