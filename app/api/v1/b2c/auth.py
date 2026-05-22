from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_buyer, get_store, hash_password, iso, parse_deep, utcnow, verify_password
from app.core.store import NeoMarketStore, ServiceError

router = APIRouter()

@router.post("/auth/register")
async def b2c_register(payload: dict[str, Any], request: Request):
    store = get_store(request)
    try:
        required = ["email", "password", "first_name"]
        for field in required:
            if not payload.get(field):
                raise ServiceError("VALIDATION_ERROR", f"Field '{field}' is required", 400)
        buyer = store.create_buyer(
            {
                "email": payload["email"],
                "password_hash": hash_password(payload["password"]),
                "first_name": payload["first_name"],
                "last_name": payload.get("last_name"),
                "phone": payload.get("phone"),
            }
        )
        return JSONResponse(status_code=201, content=jsonable_encoder(store.issue_tokens(buyer["id"], "buyer")))
    except ServiceError as exc:
        return error_response(exc)


@router.post("/auth/login")
async def b2c_login(payload: dict[str, Any], request: Request, x_session_id: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer = next((item for item in store.buyers.values() if item["email"] == payload.get("email")), None)
        if not buyer or not verify_password(payload.get("password", ""), buyer["password_hash"]):
            raise ServiceError("UNAUTHORIZED", "Invalid credentials", 401)
        if x_session_id:
            store.merge_cart(buyer["id"], x_session_id)
        return store.issue_tokens(buyer["id"], "buyer")
    except ServiceError as exc:
        return error_response(exc)


@router.post("/auth/refresh")
async def b2c_refresh(payload: dict[str, Any], request: Request):
    store = get_store(request)
    try:
        return store.refresh_pair(payload.get("refresh_token", ""))
    except ServiceError as exc:
        return error_response(exc)


@router.post("/auth/logout", status_code=204)
async def b2c_logout(payload: dict[str, Any], request: Request):
    get_store(request).revoke_refresh(payload.get("refresh_token", ""))
    return Response(status_code=204)



