from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_store
from app.core.store import ServiceError

from .buyers import buyer_id_from_auth

router = APIRouter()

@router.get("/notifications")
async def b2c_notifications(request: Request, authorization: Optional[str] = Header(None), limit: int = 20, offset: int = 0, unread_only: bool = False):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        items = store.notifications.get(buyer_id, [])
        if unread_only:
            items = [item for item in items if not item["is_read"]]
        total = len(items)
        unread_count = len([item for item in store.notifications.get(buyer_id, []) if not item["is_read"]])
        return {"items": store.clone(items[offset : offset + limit]), "total_count": total, "unread_count": unread_count, "limit": limit, "offset": offset}
    except ServiceError as exc:
        return error_response(exc)


@router.post("/notifications/{notification_id}/read", status_code=204)
async def b2c_notification_read(notification_id: str, request: Request, authorization: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        buyer_id = buyer_id_from_auth(store, authorization)
        for item in store.notifications.get(buyer_id, []):
            if item["id"] == notification_id:
                item["is_read"] = True
                return Response(status_code=204)
        raise ServiceError("NOT_FOUND", "Notification not found", 404)
    except ServiceError as exc:
        return error_response(exc)




