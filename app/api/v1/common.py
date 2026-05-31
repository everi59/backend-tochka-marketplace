from __future__ import annotations

from typing import Any, Optional

from fastapi import Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.auth import extract_bearer, hash_password, verify_password
from app.core.store import NeoMarketStore, ServiceError, iso, utcnow


def error_response(exc: ServiceError) -> JSONResponse:
    payload: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.details:
        payload["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(payload))


def parse_deep(prefix: str, query_params: list[tuple[str, str]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in query_params:
        if not key.startswith(prefix + "[") or not key.endswith("]"):
            continue
        inner = key[len(prefix) + 1 : -1]
        if inner.startswith("attributes]["):
            attr = inner[len("attributes][") :]
            result.setdefault("attributes", {})
            bucket = result["attributes"].setdefault(attr, [])
            bucket.append(value)
            continue
        if inner in result:
            if isinstance(result[inner], list):
                result[inner].append(value)
            else:
                result[inner] = [result[inner], value]
        else:
            result[inner] = value
    return result


def get_store(request: Request) -> NeoMarketStore:
    return request.app.state.store


def get_seller(store: NeoMarketStore, authorization: Optional[str]) -> dict[str, Any]:
    token = extract_bearer(authorization)
    return store.auth_subject(token, role="seller")


def get_buyer(store: NeoMarketStore, authorization: Optional[str]) -> dict[str, Any]:
    token = extract_bearer(authorization)
    return store.auth_subject(token, role="buyer")
