from app.infrastructure.database.models.base import Base

# 1. Сначала категории (не зависят от других)
from app.infrastructure.database.models.category import Category

# 2. Потом продукты (зависят от категорий)
from app.infrastructure.database.models.product import Product, ProductImage, ProductCharacteristic

# 3. Потом SKU (зависят от продуктов)
from app.infrastructure.database.models.sku import Sku, SkuImage, SkuCharacteristic

# 4. Потом остальные (зависят от продуктов/SKU)
from app.infrastructure.database.models.favorite import Favorite
from app.infrastructure.database.models.collection import Collection, collection_products
from app.infrastructure.database.models.cart import Cart, CartItem
from app.infrastructure.database.models.order import Order, OrderItem, OrderStatus
from app.infrastructure.database.models.banner import Banner, BannerEvent
from app.infrastructure.database.models.moderation import ModerationQueue, ModerationDecision, ModerationStatus, ProductBlockingReason
from app.infrastructure.database.models.invoice import Invoice, InvoiceItem, InvoiceStatus

__all__ = [
    "Base",
    "Category",
    "Product",
    "ProductImage",
    "ProductCharacteristic",
    "Sku",
    "SkuImage",
    "SkuCharacteristic",
    "Favorite",
    "Collection",
    "collection_products",
    "Cart",
    "CartItem",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Banner",
    "BannerEvent",
    "ModerationQueue",
    "ModerationDecision",
    "ModerationStatus",
    "ProductBlockingReason",
    "Invoice",
    "InvoiceItem",
    "InvoiceStatus",
]