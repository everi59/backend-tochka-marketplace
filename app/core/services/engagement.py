from __future__ import annotations

from typing import Any, Optional

from app.core.base import ServiceError, iso, utcnow
from app.core.services.base import BaseService


class EngagementService(BaseService):
    def emit_b2b_event(self, event: dict[str, Any], process: bool = True) -> None:
        self.store.b2b_events.append(self.store.clone(event))
        if process:
            self.handle_b2b_event(event)

    def emit_moderation_event(self, event: dict[str, Any]) -> None:
        self.store.moderation_events.append(self.store.clone(event))

    def notify(self, buyer_id: str, notification_type: str, title: str, body: str, payload: dict[str, Any]) -> None:
        notification = {
            'id': self.store.new_id(),
            'type': notification_type,
            'title': title,
            'body': body,
            'payload': payload,
            'is_read': False,
            'created_at': iso(utcnow()),
        }
        self.store.notifications.setdefault(buyer_id, []).insert(0, notification)

    def add_favorite(self, buyer_id: str, product_id: str) -> None:
        self.store.product_service.require_product(product_id)
        self.store.favorites.setdefault(buyer_id, set()).add(product_id)

    def remove_favorite(self, buyer_id: str, product_id: str) -> None:
        self.store.favorites.setdefault(buyer_id, set()).discard(product_id)

    def subscribe_product(self, buyer_id: str, product_id: str, events: list[str]) -> None:
        self.store.product_service.require_product(product_id)
        self.store.subscriptions.setdefault(buyer_id, {})[product_id] = set(events)

    def unsubscribe_product(self, buyer_id: str, product_id: str) -> None:
        self.store.subscriptions.setdefault(buyer_id, {}).pop(product_id, None)

    def handle_b2b_event(self, event: dict[str, Any]) -> None:
        key = event['idempotency_key']
        if key in self.store.event_idempotency:
            raise ServiceError('CONFLICT', 'Duplicate event', 409)
        self.store.event_idempotency[key] = {'accepted_at': iso(utcnow())}
        event_type = event['event_type']
        payload = event['payload']
        if event_type in {'PRODUCT_BLOCKED', 'PRODUCT_HARD_BLOCKED', 'PRODUCT_DELETED'}:
            product = self.store.product_service.require_product(payload['product_id'])
            if event_type == 'PRODUCT_DELETED':
                product['deleted'] = True
                unavailable_reason = 'deleted'
            else:
                product['status'] = 'HARD_BLOCKED' if event_type == 'PRODUCT_HARD_BLOCKED' else 'BLOCKED'
                unavailable_reason = 'blocked'
            for cart in self.store.carts.values():
                availability = cart.setdefault('item_availability', {})
                for sku_id in list(cart['items'].keys()):
                    if self.store.skus[sku_id]['product_id'] == product['id']:
                        availability[sku_id] = {'available': False, 'unavailable_reason': unavailable_reason}
            for buyer_id, product_map in self.store.subscriptions.items():
                if product['id'] in product_map:
                    self.notify(buyer_id, 'SYSTEM', 'Product unavailable', product['title'], {'product_id': product['id']})
        elif event_type in {'SKU_OUT_OF_STOCK', 'SKU_BACK_IN_STOCK'}:
            sku = self.store.product_service.require_sku(payload['sku_id'])
            sku['stock_quantity'] = payload['available_quantity'] + sku['reserved_quantity']
            if event_type == 'SKU_BACK_IN_STOCK':
                product = self.store.product_service.require_product(payload['product_id'])
                for buyer_id, product_map in self.store.subscriptions.items():
                    if product['id'] in product_map and 'BACK_IN_STOCK' in product_map[product['id']]:
                        self.notify(buyer_id, 'BACK_IN_STOCK', 'Back in stock', product['title'], {'product_id': product['id']})
        elif event_type == 'PRICE_CHANGED':
            sku = self.store.product_service.require_sku(payload['sku_id'])
            old_effective = sku['price'] - sku['discount']
            sku['price'] = payload['new_price']
            product = self.store.product_service.require_product(payload['product_id'])
            if payload['new_price'] < payload['old_price']:
                for buyer_id, product_map in self.store.subscriptions.items():
                    if product['id'] in product_map and 'PRICE_DROP' in product_map[product['id']]:
                        self.notify(buyer_id, 'PRICE_DROP', 'Price dropped', product['title'], {'product_id': product['id'], 'old_price': old_effective, 'new_price': payload['new_price']})

    def handle_moderation_event(self, event: dict[str, Any]) -> None:
        key = event['idempotency_key']
        if key in self.store.moderation_idempotency:
            return
        self.store.moderation_idempotency[key] = {'accepted_at': iso(utcnow())}
        product = self.store.product_service.require_product(event['product_id'])
        event_type = event.get('event_type') or event.get('status')
        if event_type == 'MODERATED':
            product['status'] = 'MODERATED'
            product['blocking_reason_id'] = None
            product['blocking_reason'] = None
            product['field_reports'] = []
            product['moderator_comment'] = event.get('moderator_comment')
        elif event_type == 'DELETED':
            product['deleted'] = True
            product['moderator_comment'] = event.get('moderator_comment')
        elif event_type == 'EDITED':
            product['status'] = 'ON_MODERATION'
            product['moderator_comment'] = event.get('moderator_comment')
        else:
            product['status'] = 'HARD_BLOCKED' if event.get('hard_block') else 'BLOCKED'
            blocking_reason = event.get('blocking_reason')
            product['blocking_reason'] = self.store.clone(blocking_reason)
            product['blocking_reason_id'] = event.get('blocking_reason_id') or (blocking_reason or {}).get('id')
            product['field_reports'] = self.store.clone(event.get('field_reports') or [])
            product['moderator_comment'] = event.get('moderator_comment')
            self.emit_b2b_event(
                self.store.product_service._b2c_event(
                    'PRODUCT_BLOCKED',
                    {'product_id': product['id'], 'sku_ids': list(product['skus'])},
                )
            )
        product['updated_at'] = utcnow()
