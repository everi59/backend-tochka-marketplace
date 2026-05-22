from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_store, iso, utcnow
from app.core.store import ServiceError
from .buyers import buyer_id_from_auth

router = APIRouter()


@router.get("/buyers/me/addresses")
async def b2c_addresses(request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        return store.clone(store.addresses.get(buyer_id, []))
    except ServiceError as exc:
        return error_response(exc)


@router.post("/buyers/me/addresses")
async def b2c_address_create(payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        address = store.clone(payload)
        address["id"] = store.new_id()
        address["created_at"] = iso(utcnow())
        store.addresses.setdefault(buyer_id, []).append(address)
        return JSONResponse(status_code=201, content=jsonable_encoder(address))
    except ServiceError as exc:
        return error_response(exc)


@router.patch("/buyers/me/addresses/{address_id}")
async def b2c_address_patch(address_id: str, payload: dict[str, Any], request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        for address in store.addresses.get(buyer_id, []):
            if address["id"] == address_id:
                address.update(payload)
                return address
        raise ServiceError("NOT_FOUND", "Address not found", 404)
    except ServiceError as exc:
        return error_response(exc)


@router.delete("/buyers/me/addresses/{address_id}", status_code=204)
async def b2c_address_delete(address_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        before = len(store.addresses.get(buyer_id, []))
        store.addresses[buyer_id] = [item for item in store.addresses.get(buyer_id, []) if item["id"] != address_id]
        if len(store.addresses.get(buyer_id, [])) == before:
            raise ServiceError("NOT_FOUND", "Address not found", 404)
        return Response(status_code=204)
    except ServiceError as exc:
        return error_response(exc)



