from __future__ import annotations

from typing import Any, Optional

from app.core.base import ServiceError, iso, utcnow
from app.core.services.base import BaseService


class ProductService(BaseService):
    def _slugify(self, title: str) -> str:
        return title.lower().replace(' ', '-')

    def _moderation_event(self, product_id: str, event_type: str) -> dict[str, Any]:
        product = self.store.products.get(product_id, {})
        return {
            'idempotency_key': self.store.new_id(),
            'event_type': event_type,
            'occurred_at': iso(utcnow()),
            'payload': {
                'product_id': product_id,
                'seller_id': product.get('seller_id'),
                'json_after': self.store.clone(product),
            },
        }

    def _b2c_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            'idempotency_key': self.store.new_id(),
            'event_type': event_type,
            'occurred_at': iso(utcnow()),
            'payload': payload,
        }

    def _remove_sku_from_carts(self, sku_id: str) -> None:
        for cart in self.store.carts.values():
            cart['items'].pop(sku_id, None)

    def create_product(self, seller_id: str, data: dict[str, Any]) -> dict[str, Any]:
        if data['category_id'] not in self.store.categories:
            raise ServiceError('NOT_FOUND', 'Category not found', 404)
        if data.get('images') is None:
            data['images'] = []
        slug = data.get('slug') or self._slugify(data['title'])
        if any(product['seller_id'] == seller_id and product['slug'] == slug for product in self.store.products.values()):
            raise ServiceError('CONFLICT', 'Product slug already exists', 409)
        now = utcnow()
        product = {
            'id': self.store.new_id(),
            'seller_id': seller_id,
            'category_id': data['category_id'],
            'title': data['title'],
            'slug': slug,
            'description': data.get('description'),
            'status': 'CREATED',
            'deleted': False,
            'blocking_reason_id': None,
            'moderator_comment': None,
            'images': [],
            'characteristics': [],
            'skus': [],
            'created_at': now,
            'updated_at': now,
        }
        for image in data.get('images', []):
            product['images'].append(self._make_image(image))
        for characteristic in data.get('characteristics', []):
            product['characteristics'].append(self._make_characteristic(characteristic))
        self.store.products[product['id']] = product
        return self.store.clone(product)

    def update_product(self, seller_id: str, product_id: str, data: dict[str, Any]) -> dict[str, Any]:
        product = self.require_product(product_id)
        self.ensure_seller_owns_product(seller_id, product)
        if product['status'] == 'HARD_BLOCKED':
            raise ServiceError('FORBIDDEN', 'Product is hard blocked', 403)
        for key in ('title', 'description', 'category_id'):
            if key in data and data[key] is not None:
                product[key] = data[key]
        if 'characteristics' in data and data['characteristics'] is not None:
            product['characteristics'] = [self._make_characteristic(item) for item in data['characteristics']]
        if product['status'] in {'MODERATED', 'BLOCKED'}:
            product['status'] = 'ON_MODERATION'
            self.store.engagement_service.emit_moderation_event(self._moderation_event(product['id'], 'PRODUCT_EDITED'))
        product['updated_at'] = utcnow()
        return self.store.clone(product)

    def delete_product(self, seller_id: str, product_id: str) -> None:
        product = self.require_product(product_id)
        self.ensure_seller_owns_product(seller_id, product)
        if product['deleted']:
            raise ServiceError('BAD_REQUEST', 'Product already deleted', 400)
        if product['status'] == 'HARD_BLOCKED':
            raise ServiceError('FORBIDDEN', 'Product is hard blocked', 403)
        product['deleted'] = True
        product['updated_at'] = utcnow()
        self.store.engagement_service.emit_moderation_event(self._moderation_event(product['id'], 'PRODUCT_DELETED'))
        self.store.engagement_service.emit_b2b_event(
            self._b2c_event('PRODUCT_DELETED', {'product_id': product['id'], 'sku_ids': list(product['skus'])})
        )

    def create_sku(self, seller_id: str, data: dict[str, Any]) -> dict[str, Any]:
        product = self.require_product(data['product_id'])
        self.ensure_seller_owns_product(seller_id, product)
        if product['status'] == 'HARD_BLOCKED':
            raise ServiceError('FORBIDDEN', 'Product is hard blocked', 403)
        if not data.get('name'):
            raise ServiceError('BAD_REQUEST', 'name is required', 400)
        if int(data.get('price', 0)) <= 0:
            raise ServiceError('BAD_REQUEST', 'price must be a positive integer', 400)
        images_data = data.get('images') or ([{'url': data['image'], 'ordering': 0}] if data.get('image') else [])
        now = utcnow()
        sku = {
            'id': self.store.new_id(),
            'product_id': data['product_id'],
            'name': data['name'],
            'price': int(data['price']),
            'discount': int(data.get('discount', 0)),
            'cost_price': int(data['cost_price']) if data.get('cost_price') is not None else None,
            'stock_quantity': int(data.get('stock_quantity', 0)),
            'reserved_quantity': 0,
            'article': data.get('article'),
            'images': [self._make_image(item) for item in images_data],
            'characteristics': [self._make_characteristic(item) for item in data.get('characteristics', [])],
            'created_at': now,
            'updated_at': now,
        }
        self.store.skus[sku['id']] = sku
        if not product['skus']:
            product['status'] = 'ON_MODERATION'
            self.store.engagement_service.emit_moderation_event(self._moderation_event(product['id'], 'PRODUCT_CREATED'))
        elif product['status'] in {'MODERATED', 'BLOCKED'}:
            product['status'] = 'ON_MODERATION'
            self.store.engagement_service.emit_moderation_event(self._moderation_event(product['id'], 'PRODUCT_EDITED'))
        product['skus'].append(sku['id'])
        product['updated_at'] = now
        return self.store.clone(sku)

    def update_sku(self, seller_id: str, sku_id: str, data: dict[str, Any]) -> dict[str, Any]:
        sku = self.require_sku(sku_id)
        product = self.require_product(sku['product_id'])
        self.ensure_seller_owns_product(seller_id, product)
        if product['status'] == 'HARD_BLOCKED':
            raise ServiceError('FORBIDDEN', 'Product is hard blocked', 403)
        for key in ('name', 'article'):
            if key in data and data[key] is not None:
                sku[key] = data[key]
        for key in ('price', 'discount', 'cost_price'):
            if key in data and data[key] is not None:
                sku[key] = int(data[key])
        if 'characteristics' in data and data['characteristics'] is not None:
            sku['characteristics'] = [self._make_characteristic(item) for item in data['characteristics']]
        if product['status'] in {'MODERATED', 'BLOCKED'}:
            product['status'] = 'ON_MODERATION'
            self.store.engagement_service.emit_moderation_event(self._moderation_event(product['id'], 'PRODUCT_EDITED'))
        sku['updated_at'] = utcnow()
        product['updated_at'] = utcnow()
        return self.store.clone(sku)

    def delete_sku(self, seller_id: str, sku_id: str) -> None:
        sku = self.require_sku(sku_id)
        product = self.require_product(sku['product_id'])
        self.ensure_seller_owns_product(seller_id, product)
        if product['status'] == 'HARD_BLOCKED':
            raise ServiceError('FORBIDDEN', 'Product is hard blocked', 403)
        if sku['reserved_quantity'] > 0:
            raise ServiceError('CONFLICT', 'There are active reservations', 409)
        if product['status'] == 'MODERATED' and self.active_quantity(sku) > 0:
            self.store.engagement_service.emit_b2b_event(
                self._b2c_event('SKU_OUT_OF_STOCK', {'sku_id': sku['id'], 'product_id': product['id'], 'available_quantity': 0})
            )
        self._remove_sku_from_carts(sku_id)
        product['skus'] = [item for item in product['skus'] if item != sku_id]
        if not product['skus'] and product['status'] == 'ON_MODERATION':
            product['status'] = 'CREATED'
            self.store.engagement_service.emit_moderation_event(self._moderation_event(product['id'], 'PRODUCT_DELETED'))
        product['updated_at'] = utcnow()
        del self.store.skus[sku_id]

    def adjust_stock(self, sku_id: str, delta: int) -> None:
        sku = self.require_sku(sku_id)
        sku['stock_quantity'] = max(sku['stock_quantity'] + delta, 0)
        sku['updated_at'] = utcnow()

    def active_quantity(self, sku: dict[str, Any]) -> int:
        return max(int(sku['stock_quantity']) - int(sku['reserved_quantity']), 0)

    def require_product(self, product_id: str) -> dict[str, Any]:
        product = self.store.products.get(product_id)
        if not product:
            raise ServiceError('NOT_FOUND', 'Product not found', 404)
        return product

    def require_sku(self, sku_id: str) -> dict[str, Any]:
        sku = self.store.skus.get(sku_id)
        if not sku:
            raise ServiceError('NOT_FOUND', 'SKU not found', 404)
        return sku

    def ensure_seller_owns_product(self, seller_id: str, product: dict[str, Any]) -> None:
        if product['seller_id'] != seller_id:
            raise ServiceError('NOT_FOUND', 'Product not found', 404)

    def product_response_b2b(self, product_id: str, public: bool = False) -> dict[str, Any]:
        product = self.require_product(product_id)
        skus = [self.sku_response_b2b(sku_id, public=public) for sku_id in product['skus']]
        payload = {
            'id': product['id'],
            'seller_id': product['seller_id'],
            'category_id': product['category_id'],
            'title': product['title'],
            'slug': product['slug'],
            'description': product['description'],
            'status': product['status'],
            'blocked': product['status'] in {'BLOCKED', 'HARD_BLOCKED'},
            'blocking_reason': product.get('blocking_reason'),
            'field_reports': self.store.clone(product.get('field_reports', [])),
            'images': self.store.clone(product['images']),
            'characteristics': self.store.clone(product['characteristics']),
            'skus': skus,
            'created_at': iso(product['created_at']),
            'updated_at': iso(product['updated_at']),
        }
        if not public:
            payload.update(
                {
                    'deleted': product['deleted'],
                    'blocking_reason_id': product['blocking_reason_id'],
                    'moderator_comment': product['moderator_comment'],
                }
            )
        return payload

    def sku_response_b2b(self, sku_id: str, public: bool = False) -> dict[str, Any]:
        sku = self.require_sku(sku_id)
        payload = {
            'id': sku['id'],
            'product_id': sku['product_id'],
            'name': sku['name'],
            'price': sku['price'],
            'discount': sku['discount'],
            'stock_quantity': sku['stock_quantity'],
            'active_quantity': self.active_quantity(sku),
            'article': sku['article'],
            'images': self.store.clone(sku['images']),
            'characteristics': self.store.clone(sku['characteristics']),
        }
        if public:
            return payload
        payload.update(
            {
                'cost_price': sku['cost_price'],
                'reserved_quantity': sku['reserved_quantity'],
                'created_at': iso(sku['created_at']),
                'updated_at': iso(sku['updated_at']),
            }
        )
        return payload

    def list_seller_products(self, seller_id: str, limit: int, offset: int, status: Optional[str], include_deleted: bool) -> dict[str, Any]:
        products = [p for p in self.store.products.values() if p['seller_id'] == seller_id]
        if status:
            products = [p for p in products if p['status'] == status]
        if not include_deleted:
            products = [p for p in products if not p['deleted']]
        total = len(products)
        items = []
        for product in products[offset : offset + limit]:
            min_price = None
            if product['skus']:
                min_price = min(self.store.skus[sku_id]['price'] for sku_id in product['skus'])
            items.append(
                {
                    'id': product['id'],
                    'title': product['title'],
                    'slug': product['slug'],
                    'status': product['status'],
                    'category_id': product['category_id'],
                    'deleted': product['deleted'],
                    'created_at': iso(product['created_at']),
                    'min_price': min_price,
                    'cover_image': product['images'][0]['url'] if product['images'] else None,
                }
            )
        return {'items': items, 'total_count': total, 'limit': limit, 'offset': offset}

    def _make_image(self, source: dict[str, Any]) -> dict[str, Any]:
        return {
            'id': source.get('image_id') or self.store.new_id(),
            'url': source['url'],
            'alt': source.get('alt', ''),
            'ordering': int(source.get('ordering', 0)),
            'is_main': bool(source.get('ordering', 0) == 0),
        }

    def _make_characteristic(self, source: dict[str, Any]) -> dict[str, Any]:
        return {
            'id': source.get('id', self.store.new_id()),
            'name': source['name'],
            'value': source['value'],
        }
