from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from typing import Any
from uuid import uuid4

from app.core.base import ServiceError, iso, utcnow
from app.core.services import AuthService, CartService, CatalogService, CategoryService, CommerceService, EngagementService, ProductService
from app.core.state import NeoMarketState


class NeoMarketStore:
    def __init__(self) -> None:
        self._service_names = (
            'auth_service',
            'category_service',
            'product_service',
            'catalog_service',
            'cart_service',
            'commerce_service',
            'engagement_service',
        )
        self.reset()

    def reset(self) -> None:
        self.state = NeoMarketState()
        self.auth_service = AuthService(self)
        self.category_service = CategoryService(self)
        self.product_service = ProductService(self)
        self.catalog_service = CatalogService(self)
        self.cart_service = CartService(self)
        self.commerce_service = CommerceService(self)
        self.engagement_service = EngagementService(self)
        self._seed_defaults()

    def __getattr__(self, name: str) -> Any:
        if 'state' in self.__dict__ and hasattr(self.state, name):
            return getattr(self.state, name)
        for service_name in self.__dict__.get('_service_names', ()):
            service = self.__dict__.get(service_name)
            if service is not None and hasattr(service, name):
                return getattr(service, name)
        raise AttributeError(name)

    def new_id(self) -> str:
        return str(uuid4())

    def clone(self, value: Any) -> Any:
        return deepcopy(value)

    def _seed_defaults(self) -> None:
        root_id = self.new_id()
        phones_id = self.new_id()
        accessories_id = self.new_id()
        root = {'id': root_id, 'name': 'Электроника', 'parent_id': None, 'is_active': True, 'created_at': utcnow()}
        phones = {'id': phones_id, 'name': 'Смартфоны', 'parent_id': root_id, 'is_active': True, 'created_at': utcnow()}
        accessories = {'id': accessories_id, 'name': 'Аксессуары', 'parent_id': root_id, 'is_active': True, 'created_at': utcnow()}
        for category in (root, phones, accessories):
            self.categories[category['id']] = category

        seller = self.create_seller(
            {
                'email': 'seller@neomarket.local',
                'password_hash': 'seed',
                'first_name': 'Seed',
                'last_name': 'Seller',
                'middle_name': None,
                'company_name': 'Seed Company',
                'inn': '1234567890',
                'phone': '+79990000000',
            },
            prehashed=True,
        )
        product = self.create_product(
            seller['id'],
            {
                'title': 'iPhone 15',
                'description': 'Флагманский смартфон Apple',
                'category_id': phones_id,
                'slug': 'iphone-15',
                'images': [],
                'characteristics': [
                    {'name': 'brand', 'value': 'apple'},
                    {'name': 'memory', 'value': '256'},
                ],
            },
        )
        sku = self.create_sku(
            seller['id'],
            {
                'product_id': product['id'],
                'name': 'iPhone 15 256GB Black',
                'price': 9999000,
                'discount': 100000,
                'cost_price': 7500000,
                'article': 'APL-IP15-256-BLK',
                'images': [],
                'characteristics': [
                    {'name': 'color', 'value': 'black'},
                    {'name': 'memory', 'value': '256'},
                ],
            },
        )
        self.adjust_stock(sku['id'], 10)
        self.products[product['id']]['status'] = 'MODERATED'
        self.state.banners = [
            {
                'id': self.new_id(),
                'title': 'Летняя распродажа',
                'image_url': 'https://example.com/banner.jpg',
                'link': 'https://example.com/sale',
                'ordering': 1,
                'active_from': iso(utcnow()),
                'active_to': iso(utcnow() + timedelta(days=30)),
            }
        ]
        self.state.collections = [
            {
                'id': self.new_id(),
                'name': 'Хиты недели',
                'description': 'Популярные товары',
                'products': [self.catalog_product_card(product['id'])],
            }
        ]
