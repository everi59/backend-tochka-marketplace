from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_seller, get_store, hash_password, parse_deep, verify_password
from app.core.store import ServiceError

router = APIRouter()


@router.post("/auth/register")
async def b2b_register(payload: dict[str, Any], request: Request):
    store = get_store(request)
    try:
        required = ["email", "password", "first_name", "last_name", "company_name", "inn"]
        for field in required:
            if not payload.get(field):
                raise ServiceError("VALIDATION_ERROR", f"Field '{field}' is required", 422)
        seller = store.create_seller(
            {
                "email": payload["email"],
                "password_hash": hash_password(payload["password"]),
                "first_name": payload["first_name"],
                "last_name": payload["last_name"],
                "middle_name": payload.get("middle_name"),
                "company_name": payload["company_name"],
                "inn": payload["inn"],
                "phone": payload.get("phone"),
            }
        )
        return JSONResponse(status_code=201, content=jsonable_encoder(store.issue_tokens(seller["id"], "seller")))
    except ServiceError as exc:
        return error_response(exc)


@router.post("/auth/login")
async def b2b_login(payload: dict[str, Any], request: Request):
    store = get_store(request)
    try:
        seller = next((item for item in store.sellers.values() if item["email"] == payload.get("email")), None)
        if not seller or not verify_password(payload.get("password", ""), seller["password_hash"]):
            raise ServiceError("UNAUTHORIZED", "Invalid credentials", 401)
        return store.issue_tokens(seller["id"], "seller")
    except ServiceError as exc:
        return error_response(exc)


@router.post("/auth/refresh")
async def b2b_refresh(payload: dict[str, Any], request: Request):
    store = get_store(request)
    try:
        return store.refresh_pair(payload.get("refresh_token", ""))
    except ServiceError as exc:
        return error_response(exc)


@router.post("/auth/logout", status_code=204)
async def b2b_logout(payload: dict[str, Any], request: Request):
    store = get_store(request)
    store.revoke_refresh(payload.get("refresh_token", ""))
    return Response(status_code=204)

