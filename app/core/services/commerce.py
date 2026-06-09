from __future__ import annotations

from typing import Any, Optional

from app.core.base import ServiceError, iso, utcnow
from app.core.services.base import BaseService


class CommerceService(BaseService):
    def create_invoice(self, seller_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        if not items:
            raise ServiceError('BAD_REQUEST', 'Invoice items must not be empty', 400)
        now = utcnow()
        invoice = {
            'id': self.store.new_id(),
            'seller_id': seller_id,
            'status': 'CREATED',
            'items': [],
            'created_at': now,
            'updated_at': now,
            'accepted_at': None,
            'accepted_by': None,
        }
        for item in items:
            sku = self.store.product_service.require_sku(item['sku_id'])
            product = self.store.product_service.require_product(sku['product_id'])
            self.store.product_service.ensure_seller_owns_product(seller_id, product)
            if product['status'] != 'MODERATED' or product['deleted']:
                raise ServiceError('BAD_REQUEST', 'Only moderated SKU can be added to invoice', 400)
            invoice['items'].append({'id': self.store.new_id(), 'sku_id': sku['id'], 'quantity': int(item['quantity']), 'accepted_quantity': 0})
        self.store.invoices[invoice['id']] = invoice
        return self.store.clone(invoice)

    def accept_invoice(self, invoice_id: str, accepted_items: Optional[list[dict[str, Any]]]) -> dict[str, Any]:
        invoice = self.store.invoices.get(invoice_id)
        if not invoice:
            raise ServiceError('NOT_FOUND', 'Invoice not found', 404)
        accepted_map = {item['invoice_item_id']: int(item['accepted_quantity']) for item in accepted_items or []}
        all_full = True
        any_partial = False
        for item in invoice['items']:
            accepted_qty = accepted_map.get(item['id'], item['quantity'])
            accepted_qty = max(0, min(item['quantity'], accepted_qty))
            item['accepted_quantity'] = accepted_qty
            self.store.product_service.adjust_stock(item['sku_id'], accepted_qty)
            if accepted_qty != item['quantity']:
                all_full = False
                any_partial = True
        invoice['status'] = 'ACCEPTED' if all_full else 'PARTIALLY_ACCEPTED' if any_partial else 'CREATED'
        invoice['updated_at'] = utcnow()
        invoice['accepted_at'] = utcnow()
        return self.store.clone(invoice)

    def reserve_inventory(self, idempotency_key: str, order_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        existing = self.store.reserve_idempotency.get(idempotency_key)
        if existing:
            return self.store.clone(existing)
        problems = []
        for item in items:
            sku = self.store.product_service.require_sku(item['sku_id'])
            quantity = int(item['quantity'])
            if self.store.product_service.active_quantity(sku) < quantity:
                problems.append({'sku_id': sku['id'], 'available_quantity': self.store.product_service.active_quantity(sku)})
        if problems:
            raise ServiceError('CONFLICT', 'Reserve failed', 409, {'items': problems})
        for item in items:
            sku = self.store.product_service.require_sku(item['sku_id'])
            sku['reserved_quantity'] += int(item['quantity'])
        response = {'order_id': order_id, 'status': 'RESERVED', 'reserved_at': iso(utcnow())}
        self.store.reserve_idempotency[idempotency_key] = response
        return self.store.clone(response)

    def unreserve_inventory(self, order_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        for item in items:
            sku = self.store.product_service.require_sku(item['sku_id'])
            sku['reserved_quantity'] = max(0, sku['reserved_quantity'] - int(item['quantity']))
        return {'order_id': order_id, 'status': 'UNRESERVED', 'processed_at': iso(utcnow())}

    def fulfill_inventory(self, order_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        for item in items:
            sku = self.store.product_service.require_sku(item['sku_id'])
            quantity = int(item['quantity'])
            sku['reserved_quantity'] = max(0, sku['reserved_quantity'] - quantity)
            sku['stock_quantity'] = max(0, sku['stock_quantity'] - quantity)
        return {'order_id': order_id, 'status': 'FULFILLED', 'processed_at': iso(utcnow())}

    def create_order(self, buyer_id: str, payload: dict[str, Any], idempotency_key: str) -> tuple[dict[str, Any], bool]:
        current_cart = self.store.cart_service.build_cart_response(buyer_id, None)
        validation = self.store.cart_service.validate_cart(buyer_id, None)
        if not validation['is_valid']:
            raise ServiceError('CART_INVALID', 'Cart validation failed', 422, validation)
        existing = self.store.order_idempotency.get(idempotency_key)
        if existing:
            if existing['body'] != payload:
                raise ServiceError('CONFLICT', 'Idempotency key already used with different payload', 409)
            return self.store.clone(self.store.orders[existing['order_id']]), False
        addresses = {item['id']: item for item in self.store.addresses.get(buyer_id, [])}
        methods = {item['id']: item for item in self.store.payment_methods.get(buyer_id, [])}
        address = addresses.get(payload['address_id'])
        payment_method = methods.get(payload['payment_method_id'])
        if not address or not payment_method:
            raise ServiceError('BAD_REQUEST', 'Address or payment method not found', 400)
        reserve_items = [{'sku_id': item['sku_id'], 'quantity': item['quantity']} for item in current_cart['items']]
        self.reserve_inventory(idempotency_key, self.store.new_id(), reserve_items)
        now = utcnow()
        order_id = self.store.new_id()
        items = []
        for item in current_cart['items']:
            items.append({'sku_id': item['sku_id'], 'product_id': item['product_id'], 'name': item['name'], 'sku_code': item['sku_code'], 'quantity': item['quantity'], 'unit_price': item['unit_price'], 'line_total': item['line_total'], 'image_url': item['image']['url'] if item['image'] else None})
        subtotal = sum(item['line_total'] for item in items)
        order = {
            'id': order_id,
            'number': f"NM-{now.year}-{self.store.state.order_counter:06d}",
            'buyer_id': buyer_id,
            'status': 'PAID',
            'status_history': [{'status': 'CREATED', 'changed_at': iso(now), 'reason': None}, {'status': 'PAID', 'changed_at': iso(now), 'reason': None}],
            'items': items,
            'subtotal': subtotal,
            'delivery_cost': 0,
            'total': subtotal,
            'address': self.store.clone(address),
            'payment_method': self.store.clone(payment_method),
            'comment': payload.get('comment'),
            'cancel_reason': None,
            'created_at': iso(now),
            'paid_at': iso(now),
            'delivered_at': None,
        }
        self.store.orders[order_id] = order
        self.store.order_idempotency[idempotency_key] = {'order_id': order_id, 'body': self.store.clone(payload)}
        self.store.state.order_counter += 1
        self.store.cart_service.clear_cart(buyer_id, None)
        self.store.engagement_service.notify(buyer_id, 'ORDER_STATUS_CHANGED', 'Order created', f"Order {order['number']} has been paid", {'order_id': order_id})
        return self.store.clone(order), True

    def cancel_order(self, buyer_id: str, order_id: str, reason: Optional[str]) -> dict[str, Any]:
        order = self.store.orders.get(order_id)
        if not order or order['buyer_id'] != buyer_id:
            raise ServiceError('NOT_FOUND', 'Order not found', 404)
        if order['status'] not in {'CREATED', 'PAID'}:
            raise ServiceError('CONFLICT', 'Order cannot be cancelled in current status', 409)
        order['cancel_reason'] = reason
        unreserve_items = [{'sku_id': item['sku_id'], 'quantity': item['quantity']} for item in order['items']]
        try:
            self.unreserve_inventory(order_id, unreserve_items)
            order['status'] = 'CANCELLED'
            order['cancel_error'] = None
            order['status_history'].append({'status': 'CANCELLED', 'changed_at': iso(utcnow()), 'reason': reason})
        except ServiceError as exc:
            order['status'] = 'CANCEL_PENDING'
            order['cancel_error'] = {'code': exc.code, 'message': exc.message, 'details': self.store.clone(exc.details)}
            order['status_history'].append({'status': 'CANCEL_PENDING', 'changed_at': iso(utcnow()), 'reason': reason})
        title = 'Order cancelled' if order['status'] == 'CANCELLED' else 'Order cancellation pending'
        body = (
            f"Order {order['number']} has been cancelled"
            if order['status'] == 'CANCELLED'
            else f"Order {order['number']} cancellation is pending"
        )
        self.store.engagement_service.notify(buyer_id, 'ORDER_STATUS_CHANGED', title, body, {'order_id': order_id})
        return self.store.clone(order)
