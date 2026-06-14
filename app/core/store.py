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
                'images': [{'url': 'https://example.com/iphone-15.jpg', 'ordering': 0}],
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
                'images': [{'url': 'https://example.com/iphone-15-sku.jpg', 'ordering': 0}],
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
        self.state.blocking_reasons = [
            {'id': 'a7b8c9d0-1234-5678-ef01-890123456789', 'title': 'Описание не соответствует товару', 'hard_block': False},
            {'id': 'b8c9d0e1-2345-6789-f012-901234567890', 'title': 'Изображение не соответствует товару', 'hard_block': False},
            {'id': 'c9d0e1f2-3456-7890-0123-012345678901', 'title': 'Некорректная категория товара', 'hard_block': False},
            {'id': 'd0e1f2a3-4567-8901-1234-123456789012', 'title': 'Недостаточно информации о товаре', 'hard_block': False},
            {'id': 'e1f2a3b4-5678-9012-2345-234567890123', 'title': 'Нецензурные или оскорбительные материалы', 'hard_block': False},
            {'id': 'f2a3b4c5-6789-0123-3456-345678901234', 'title': 'Дублирование существующего товара', 'hard_block': False},
            {'id': 'a3b4c5d6-7890-1234-4567-456789012345', 'title': 'Некорректная цена', 'hard_block': False},
            {'id': 'b4c5d6e7-8901-2345-5678-567890123456', 'title': 'Контрафактный товар', 'hard_block': True},
            {'id': 'c5d6e7f8-9012-3456-6789-678901234567', 'title': 'Товар запрещён к продаже на территории РФ', 'hard_block': True},
            {'id': 'd6e7f8a9-0123-4567-7890-789012345678', 'title': 'Товар нарушает авторские права', 'hard_block': True},
        ]
