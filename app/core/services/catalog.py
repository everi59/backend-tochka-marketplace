from __future__ import annotations

from typing import Any, Optional

from app.core.base import ServiceError
from app.core.services.base import BaseService


class CatalogService(BaseService):
    def is_public_product(self, product: dict[str, Any]) -> bool:
        if product['status'] != 'MODERATED' or product['deleted']:
            return False
        return any(self.store.product_service.active_quantity(self.store.skus[sku_id]) > 0 for sku_id in product['skus'])

    def public_product_ids(self) -> list[str]:
        ids = []
        for product in self.store.products.values():
            if self.is_public_product(product):
                ids.append(product['id'])
        return ids

    def catalog_product_card(self, product_id: str) -> dict[str, Any]:
        product = self.store.product_service.require_product(product_id)
        sku_list = [self.store.skus[sku_id] for sku_id in product['skus']]
        available_skus = [sku for sku in sku_list if self.store.product_service.active_quantity(sku) > 0]
        prices = [sku['price'] - sku['discount'] for sku in available_skus] or [sku['price'] - sku['discount'] for sku in sku_list]
        min_price = min(prices) if prices else 0
        old_price = max((sku['price'] for sku in sku_list), default=0) if sku_list else None
        seller = self.store.sellers.get(product['seller_id'])
        return {
            'id': product['id'],
            'name': product['title'],
            'slug': product['slug'],
            'category': self.store.category_service.category_ref(product['category_id']),
            'min_price': min_price,
            'old_price': old_price if old_price and old_price != min_price else None,
            'has_stock': any(self.store.product_service.active_quantity(sku) > 0 for sku in sku_list),
            'rating': None,
            'reviews_count': 0,
            'images': self.store.clone(product['images']),
            'seller': {
                'id': seller['id'] if seller else None,
                'display_name': seller['company_name'] if seller else None,
            },
        }

    def catalog_product_detail(self, product_id: str) -> dict[str, Any]:
        product = self.store.product_service.require_product(product_id)
        detail = self.catalog_product_card(product_id)
        detail['description'] = product['description']
        detail['attributes'] = {item['name']: item['value'] for item in product['characteristics']}
        detail['skus'] = [self.catalog_sku(sku_id) for sku_id in product['skus']]
        return detail

    def catalog_sku(self, sku_id: str) -> dict[str, Any]:
        sku = self.store.product_service.require_sku(sku_id)
        return {
            'id': sku['id'],
            'name': sku['name'],
            'sku_code': sku['article'],
            'price': sku['price'] - sku['discount'],
            'old_price': sku['price'] if sku['discount'] else None,
            'available_quantity': self.store.product_service.active_quantity(sku),
            'attributes': {item['name']: item['value'] for item in sku['characteristics']},
            'images': self.store.clone(sku['images']),
        }

    def public_product_short(self, product_id: str) -> dict[str, Any]:
        product = self.store.product_service.require_product(product_id)
        return {
            'id': product['id'],
            'title': product['title'],
            'slug': product['slug'],
            'status': product['status'],
            'category_id': product['category_id'],
            'created_at': product['created_at'].isoformat().replace('+00:00', 'Z'),
        }

    def catalog_facets(self, category_id: str) -> dict[str, Any]:
        if category_id not in self.store.categories:
            raise ServiceError('NOT_FOUND', 'Category not found', 404)
        products = [
            product
            for product in self.store.products.values()
            if product['category_id'] == category_id and self.is_public_product(product)
        ]
        facets_map: dict[str, dict[str, int]] = {}
        for product in products:
            for item in product['characteristics']:
                values = facets_map.setdefault(item['name'], {})
                values[item['value']] = values.get(item['value'], 0) + 1
        facets = [
            {
                'name': name,
                'values': [{'value': value, 'count': count} for value, count in sorted(values.items())],
            }
            for name, values in sorted(facets_map.items())
        ]
        return {'category_id': category_id, 'facets': facets}

    def list_catalog_products(self, limit: int, offset: int, query: Optional[str], sort: str, filter_data: Optional[dict[str, Any]]) -> dict[str, Any]:
        allowed_sorts = {'price_asc', 'price_desc', 'new'}
        if sort not in allowed_sorts:
            raise ServiceError('BAD_REQUEST', "Invalid sort value. Allowed values: price_asc, price_desc, new", 400)
        products = [self.store.products[product_id] for product_id in self.public_product_ids()]
        if query:
            q = query.lower()
            products = [p for p in products if q in p['title'].lower() or q in p['description'].lower()]
        if filter_data:
            category_id = filter_data.get('category_id')
            if category_id:
                products = [p for p in products if p['category_id'] == category_id]
            seller_id = filter_data.get('seller_id')
            if seller_id:
                products = [p for p in products if p['seller_id'] == seller_id]
            price_min = filter_data.get('price_min')
            if price_min is not None:
                products = [p for p in products if self.catalog_product_card(p['id'])['min_price'] >= int(price_min)]
            price_max = filter_data.get('price_max')
            if price_max is not None:
                products = [p for p in products if self.catalog_product_card(p['id'])['min_price'] <= int(price_max)]
            attributes = filter_data.get('attributes') or {}
            for attr_name, attr_value in attributes.items():
                allowed = attr_value if isinstance(attr_value, list) else [attr_value]
                products = [
                    p for p in products if any(item['name'] == attr_name and item['value'] in allowed for item in p['characteristics'])
                ]
        cards = [self.catalog_product_card(product['id']) for product in products]
        if sort == 'price_asc':
            cards.sort(key=lambda item: item['min_price'])
        elif sort == 'price_desc':
            cards.sort(key=lambda item: item['min_price'], reverse=True)
        elif sort == 'new':
            cards.sort(key=lambda item: self.store.products[item['id']]['created_at'], reverse=True)
        total = len(cards)
        return {'items': cards[offset : offset + limit], 'total_count': total, 'limit': limit, 'offset': offset}
