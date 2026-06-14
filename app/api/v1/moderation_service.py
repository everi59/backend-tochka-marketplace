from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Header, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.v1.common import error_response, get_store, require_service_key
from app.core.base import ServiceError, iso, utcnow
from app.core.store import NeoMarketStore

router = APIRouter()


def _strip_private_fields(product_data: dict) -> dict:
    product_data = {**product_data}
    for sku in product_data.get('skus', []):
        sku.pop('cost_price', None)
        sku.pop('reserved_quantity', None)
    return product_data


def _compute_queue_priority(old_status: str, blocking_reason_id: Optional[str], total_active: int) -> int:
    if old_status == 'BLOCKED' and blocking_reason_id:
        return 2
    if old_status == 'MODERATED' and total_active > 0:
        return 3
    if old_status == 'MODERATED' and total_active == 0:
        return 4
    return 1


def _get_total_active(store: NeoMarketStore, product: dict) -> int:
    total = 0
    for sku_id in product.get('skus', []):
        sku = store.skus.get(sku_id)
        if sku:
            total += max(sku['stock_quantity'] - sku['reserved_quantity'], 0)
    return total


@router.post("/events/product")
async def moderation_receive_event(payload: dict[str, Any], request: Request, x_service_key: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        require_service_key(x_service_key)
        product_id = payload.get('product_id')
        seller_id = payload.get('seller_id')
        event = payload.get('event')
        if not product_id or not event:
            raise ServiceError('BAD_REQUEST', 'product_id and event are required', 400)

        card = store.moderation_cards.get(product_id)

        if event == 'CREATED':
            if card and card['status'] == 'HARD_BLOCKED':
                return Response(status_code=200)
            if card:
                raise ServiceError('BAD_REQUEST', 'Duplicate CREATED event', 400)
            product = store.products.get(product_id)
            if not product:
                raise ServiceError('NOT_FOUND', 'Product not found in B2B', 404)
            json_after = _strip_private_fields(store.product_service.product_response_b2b(product_id, public=False))
            now = utcnow()
            store.moderation_cards[product_id] = {
                'product_id': product_id,
                'seller_id': seller_id or product.get('seller_id'),
                'status': 'PENDING',
                'queue_priority': 1,
                'json_before': None,
                'json_after': json_after,
                'blocking_reason_id': None,
                'moderator_id': None,
                'moderator_comment': None,
                'field_reports': [],
                'date_created': now,
                'date_updated': now,
                'date_moderation': None,
            }
            return Response(status_code=200)

        elif event == 'EDITED':
            if not card:
                raise ServiceError('BAD_REQUEST', 'EDITED event for unknown product', 400)
            if card['status'] == 'HARD_BLOCKED':
                return Response(status_code=200)
            old_status = card['status']
            product = store.products.get(product_id)
            if not product:
                raise ServiceError('NOT_FOUND', 'Product not found in B2B', 404)
            json_after = _strip_private_fields(store.product_service.product_response_b2b(product_id, public=False))
            total_active = _get_total_active(store, product)
            queue_priority = _compute_queue_priority(old_status, card.get('blocking_reason_id'), total_active)
            now = utcnow()
            card['json_before'] = card['json_after']
            card['json_after'] = json_after
            card['status'] = 'PENDING'
            card['queue_priority'] = queue_priority
            card['moderator_id'] = None
            card['field_reports'] = []
            card['date_updated'] = now
            return Response(status_code=200)

        elif event == 'DELETED':
            if card:
                del store.moderation_cards[product_id]
            return Response(status_code=200)

        else:
            raise ServiceError('BAD_REQUEST', f'Unknown event type: {event}', 400)

    except ServiceError as exc:
        return error_response(exc)


@router.post("/product-moderation/get-next")
async def moderation_get_next(payload: dict[str, Any], request: Request, x_moderator_id: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        queue_id = payload.get('queueId')
        candidates = []
        for pid, card in store.moderation_cards.items():
            if card['status'] != 'PENDING':
                continue
            if queue_id and card['queue_priority'] != queue_id:
                continue
            candidates.append(card)
        if not candidates:
            return Response(status_code=204)
        candidates.sort(key=lambda c: c['date_updated'])
        card = candidates[0]
        card['status'] = 'IN_REVIEW'
        card['moderator_id'] = x_moderator_id or 'unknown'
        card['date_updated'] = utcnow()
        blocking_history = None
        if card.get('blocking_reason_id') and card.get('json_before'):
            reason = next((r for r in store.blocking_reasons if r['id'] == card['blocking_reason_id']), None)
            blocking_history = {
                'blocking_reason': reason,
                'moderator_comment': card.get('moderator_comment'),
                'field_reports': card.get('field_reports', []),
            }
        return {
            'product_moderation_id': card['product_id'],
            'product_id': card['product_id'],
            'seller_id': card['seller_id'],
            'status': card['status'],
            'queue_priority': card['queue_priority'],
            'json_before': card['json_before'],
            'json_after': card['json_after'],
            'blocking_history': blocking_history,
            'date_created': iso(card['date_created']),
            'date_updated': iso(card['date_updated']),
        }
    except Exception as exc:
        return error_response(ServiceError('INTERNAL_ERROR', str(exc), 500))


@router.post("/products/{product_id}/approve")
async def moderation_approve(product_id: str, payload: Optional[dict[str, Any]], request: Request, x_moderator_id: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        card = store.moderation_cards.get(product_id)
        if not card:
            raise ServiceError('NOT_FOUND', 'Product not found in moderation queue', 404)
        if card['status'] == 'HARD_BLOCKED':
            raise ServiceError('CONFLICT', 'Product is permanently blocked', 409)
        if card['status'] != 'IN_REVIEW':
            raise ServiceError('CONFLICT', 'Product is not in review', 409)
        if card['moderator_id'] != (x_moderator_id or 'unknown'):
            raise ServiceError('FORBIDDEN', 'This moderation card is not assigned to you', 403)

        product = store.products.get(product_id)

        now = utcnow()
        comment = (payload or {}).get('moderator_comment')
        card['status'] = 'MODERATED'
        card['date_moderation'] = now
        card['moderator_comment'] = comment
        card['blocking_reason_id'] = None
        card['field_reports'] = []
        card['date_updated'] = now

        store.handle_moderation_event({
            'idempotency_key': store.new_id(),
            'product_id': product_id,
            'event_type': 'MODERATED',
            'occurred_at': iso(now),
        })

        return {'product_id': product_id, 'status': 'MODERATED'}
    except ServiceError as exc:
        return error_response(exc)


@router.post("/products/{product_id}/decline")
async def moderation_decline(product_id: str, payload: dict[str, Any], request: Request, x_moderator_id: Optional[str] = Header(None)):
    store = get_store(request)
    try:
        card = store.moderation_cards.get(product_id)
        if not card:
            raise ServiceError('NOT_FOUND', 'Product not found in moderation queue', 404)
        if card['status'] == 'HARD_BLOCKED':
            raise ServiceError('CONFLICT', 'Product is permanently blocked', 409)
        if card['status'] != 'IN_REVIEW':
            raise ServiceError('CONFLICT', 'Product is not in review', 409)
        if card['moderator_id'] != (x_moderator_id or 'unknown'):
            raise ServiceError('FORBIDDEN', 'This moderation card is not assigned to you', 403)

        blocking_reason_id = payload.get('blocking_reason_id')
        if not blocking_reason_id:
            raise ServiceError('BAD_REQUEST', 'blocking_reason_id is required', 400)

        reason = next((r for r in store.blocking_reasons if r['id'] == blocking_reason_id), None)
        if not reason:
            raise ServiceError('BAD_REQUEST', 'Blocking reason not found', 400)

        now = utcnow()
        is_hard_block = reason.get('hard_block', False)
        card['status'] = 'HARD_BLOCKED' if is_hard_block else 'BLOCKED'
        card['date_moderation'] = now
        card['blocking_reason_id'] = blocking_reason_id
        card['moderator_comment'] = payload.get('moderator_comment')
        card['field_reports'] = payload.get('field_reports', [])
        card['date_updated'] = now

        store.handle_moderation_event({
            'idempotency_key': store.new_id(),
            'product_id': product_id,
            'event_type': card['status'],
            'blocking_reason': reason,
            'moderator_comment': card['moderator_comment'],
            'field_reports': card['field_reports'],
            'hard_block': is_hard_block,
            'occurred_at': iso(now),
        })

        return {'product_id': product_id, 'status': card['status']}
    except ServiceError as exc:
        return error_response(exc)


@router.get("/product-blocking-reasons")
async def moderation_blocking_reasons(request: Request):
    store = get_store(request)
    return store.blocking_reasons
