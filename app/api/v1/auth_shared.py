from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_store, hash_password, verify_password
from app.core.store import ServiceError

router = APIRouter()


def _is_seller_registration(payload: dict[str, Any]) -> bool:
    return bool(payload.get("company_name") or payload.get("inn"))


@router.post("/auth/register")
async def auth_register(payload: dict[str, Any], request: Request):
    store = get_store(request)
    try:
        if _is_seller_registration(payload):
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
async def auth_login(payload: dict[str, Any], request: Request, x_session_id: str | None = Header(None, alias="X-Session-Id")):
    store = get_store(request)
    try:
        seller = next((item for item in store.sellers.values() if item["email"] == payload.get("email")), None)
        if seller and verify_password(payload.get("password", ""), seller["password_hash"]):
            return store.issue_tokens(seller["id"], "seller")
        buyer = next((item for item in store.buyers.values() if item["email"] == payload.get("email")), None)
        if buyer and verify_password(payload.get("password", ""), buyer["password_hash"]):
            if x_session_id:
                store.cart_service.merge_cart(buyer["id"], x_session_id)
            return store.issue_tokens(buyer["id"], "buyer")
        raise ServiceError("UNAUTHORIZED", "Invalid credentials", 401)
    except ServiceError as exc:
        return error_response(exc)


@router.post("/auth/refresh")
async def auth_refresh(payload: dict[str, Any], request: Request):
    store = get_store(request)
    try:
        return store.refresh_pair(payload.get("refresh_token", ""))
    except ServiceError as exc:
        return error_response(exc)


@router.post("/auth/logout", status_code=204)
async def auth_logout(payload: dict[str, Any], request: Request):
    store = get_store(request)
    store.revoke_refresh(payload.get("refresh_token", ""))
    return Response(status_code=204)
