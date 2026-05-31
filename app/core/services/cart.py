from __future__ import annotations

from typing import Optional

from app.core.base import ServiceError, iso, utcnow
from app.core.services.base import BaseService


class CartService(BaseService):
    def cart_key(self, buyer_id: Optional[str], session_id: Optional[str]) -> str:
        if buyer_id:
            return f'buyer:{buyer_id}'
        if session_id:
            return f'guest:{session_id}'
        raise ServiceError('BAD_REQUEST', 'X-Session-Id is required for guest cart', 400)

    def ensure_cart(self, buyer_id: Optional[str], session_id: Optional[str]) -> dict[str, object]:
        key = self.cart_key(buyer_id, session_id)
        if key not in self.store.carts:
            self.store.carts[key] = {'id': key, 'buyer_id': buyer_id, 'session_id': session_id, 'items': {}, 'updated_at': utcnow()}
        return self.store.carts[key]

    def build_cart_response(self, buyer_id: Optional[str], session_id: Optional[str]) -> dict[str, object]:
        cart = self.ensure_cart(buyer_id, session_id)
        items = []
        subtotal = 0
        items_count = 0
        is_valid = True
        for sku_id, quantity in cart['items'].items():
            sku = self.store.product_service.require_sku(sku_id)
            product = self.store.product_service.require_product(sku['product_id'])
            available_quantity = self.store.product_service.active_quantity(sku)
            is_available = product['status'] == 'MODERATED' and not product['deleted'] and available_quantity > 0
            valid_quantity = quantity <= available_quantity
            line_total = (sku['price'] - sku['discount']) * quantity
            subtotal += line_total
            items_count += quantity
            is_valid = is_valid and is_available and valid_quantity
            items.append(
                {
                    'sku_id': sku['id'],
                    'product_id': product['id'],
                    'name': f"{product['title']} {sku['name']}",
                    'sku_code': sku['article'],
                    'quantity': quantity,
                    'unit_price': sku['price'] - sku['discount'],
                    'unit_price_at_add': sku['price'] - sku['discount'],
                    'line_total': line_total,
                    'available_quantity': available_quantity,
                    'is_available': is_available,
                    'image': sku['images'][0] if sku['images'] else None,
                }
            )
        return {'id': cart['id'], 'items': items, 'items_count': items_count, 'subtotal': subtotal, 'is_valid': is_valid, 'updated_at': iso(cart['updated_at'])}

    def add_cart_item(self, buyer_id: Optional[str], session_id: Optional[str], sku_id: str, quantity: int) -> dict[str, object]:
        sku = self.store.product_service.require_sku(sku_id)
        product = self.store.product_service.require_product(sku['product_id'])
        if product['status'] != 'MODERATED' or product['deleted']:
            raise ServiceError('NOT_FOUND', 'SKU not found or unavailable', 404)
        if quantity > self.store.product_service.active_quantity(sku):
            raise ServiceError('CONFLICT', 'Not enough stock', 409)
        cart = self.ensure_cart(buyer_id, session_id)
        cart['items'][sku_id] = cart['items'].get(sku_id, 0) + quantity
        cart['updated_at'] = utcnow()
        return self.build_cart_response(buyer_id, session_id)

    def patch_cart_item(self, buyer_id: Optional[str], session_id: Optional[str], sku_id: str, quantity: int) -> dict[str, object]:
        sku = self.store.product_service.require_sku(sku_id)
        if quantity > self.store.product_service.active_quantity(sku):
            raise ServiceError('CONFLICT', 'Not enough stock', 409)
        cart = self.ensure_cart(buyer_id, session_id)
        if sku_id not in cart['items']:
            raise ServiceError('NOT_FOUND', 'SKU not found in cart', 404)
        cart['items'][sku_id] = quantity
        cart['updated_at'] = utcnow()
        return self.build_cart_response(buyer_id, session_id)

    def remove_cart_item(self, buyer_id: Optional[str], session_id: Optional[str], sku_id: str) -> dict[str, object]:
        cart = self.ensure_cart(buyer_id, session_id)
        cart['items'].pop(sku_id, None)
        cart['updated_at'] = utcnow()
        return self.build_cart_response(buyer_id, session_id)

    def clear_cart(self, buyer_id: Optional[str], session_id: Optional[str]) -> None:
        cart = self.ensure_cart(buyer_id, session_id)
        cart['items'] = {}
        cart['updated_at'] = utcnow()

    def validate_cart(self, buyer_id: Optional[str], session_id: Optional[str]) -> dict[str, object]:
        cart_response = self.build_cart_response(buyer_id, session_id)
        issues = []
        for item in cart_response['items']:
            if not item['is_available']:
                issues.append({'sku_id': item['sku_id'], 'type': 'PRODUCT_BLOCKED', 'message': 'Product is unavailable'})
            elif item['quantity'] > item['available_quantity']:
                issues.append({'sku_id': item['sku_id'], 'type': 'QUANTITY_REDUCED', 'message': 'Available quantity changed', 'old_value': item['quantity'], 'new_value': item['available_quantity']})
        return {'is_valid': len(issues) == 0, 'cart': cart_response, 'issues': issues}

    def merge_cart(self, buyer_id: str, session_id: str) -> dict[str, object]:
        user_cart = self.ensure_cart(buyer_id, None)
        guest_cart = self.ensure_cart(None, session_id)
        for sku_id, quantity in guest_cart['items'].items():
            user_cart['items'][sku_id] = max(user_cart['items'].get(sku_id, 0), quantity)
        guest_cart['items'] = {}
        user_cart['updated_at'] = utcnow()
        return self.build_cart_response(buyer_id, None)
