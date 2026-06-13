from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Header, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_seller, get_store, hash_password, parse_deep, require_service_key, verify_password
from app.core.store import ServiceError

router = APIRouter()

@router.post("/inventory/reserve")
async def b2b_inventory_reserve(payload: dict[str, Any], request: Request, x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        require_service_key(x_service_key)
        return store.reserve_inventory(payload["idempotency_key"], payload["order_id"], payload["items"])
    except KeyError as exc:
        return error_response(ServiceError("VALIDATION_ERROR", f"Missing field {exc}", 422))
    except ServiceError as exc:
        return error_response(exc)


@router.post("/reserve")
async def b2b_reserve(payload: dict[str, Any], request: Request, x_service_key: Optional[str] = Header(None)):
    return await b2b_inventory_reserve(payload, request, x_service_key)


@router.post("/inventory/unreserve")
async def b2b_inventory_unreserve(payload: dict[str, Any], request: Request, x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        require_service_key(x_service_key)
        return store.unreserve_inventory(payload["order_id"], payload["items"])
    except KeyError as exc:
        return error_response(ServiceError("VALIDATION_ERROR", f"Missing field {exc}", 422))
    except ServiceError as exc:
        return error_response(exc)


@router.post("/unreserve")
async def b2b_unreserve(payload: dict[str, Any], request: Request, x_service_key: Optional[str] = Header(None)):
    return await b2b_inventory_unreserve(payload, request, x_service_key)


@router.post("/inventory/fulfill")
async def b2b_inventory_fulfill(payload: dict[str, Any], request: Request, x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        require_service_key(x_service_key)
        return store.fulfill_inventory(payload["order_id"], payload["items"])
    except KeyError as exc:
        return error_response(ServiceError("VALIDATION_ERROR", f"Missing field {exc}", 422))
    except ServiceError as exc:
        return error_response(exc)


@router.post("/fulfill")
async def b2b_fulfill(payload: dict[str, Any], request: Request, x_service_key: Optional[str] = Header(None)):
    return await b2b_inventory_fulfill(payload, request, x_service_key)
