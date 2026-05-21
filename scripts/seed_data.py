import asyncio
import sys
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.infrastructure.database.models.base import Base
from app.infrastructure.database.models.category import Category
from app.infrastructure.database.models.product import Product, ProductImage, ProductCharacteristic, ProductStatus
from app.infrastructure.database.models.sku import Sku, SkuImage, SkuCharacteristic
from app.infrastructure.config.config import DB_CONFIG


async def seed_data():

    print("Starting seed data creation...")

    engine = create_async_engine(DB_CONFIG.get_url(is_async=True))
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    try:
        async with async_session() as session:
            # ============================================
            # 1. КАТЕГОРИИ
            # ============================================
            print("\nCreating categories...")

            # Корневые категории
            electronics = Category(
                id=UUID("123e4567-e89b-12d3-a456-426614174001"),
                name="Электроника",
                slug="electronics",
                description="Электроника и гаджеты",
                is_active=True,
            )

            clothing = Category(
                id=UUID("123e4567-e89b-12d3-a456-426614174002"),
                name="Одежда",
                slug="clothing",
                description="Одежда и аксессуары",
                is_active=True,
            )

            home = Category(
                id=UUID("123e4567-e89b-12d3-a456-426614174003"),
                name="Дом и сад",
                slug="home-garden",
                description="Товары для дома и сада",
                is_active=True,
            )

            # Подкатегории электроники
            smartphones = Category(
                id=UUID("123e4567-e89b-12d3-a456-426614174011"),
                name="Смартфоны",
                slug="smartphones",
                description="Мобильные телефоны",
                parent_id=electronics.id,
                is_active=True,
            )

            laptops = Category(
                id=UUID("123e4567-e89b-12d3-a456-426614174012"),
                name="Ноутбуки",
                slug="laptops",
                description="Ноутбуки и ультрабуки",
                parent_id=electronics.id,
                is_active=True,
            )

            tablets = Category(
                id=UUID("123e4567-e89b-12d3-a456-426614174013"),
                name="Планшеты",
                slug="tablets",
                description="Планшетные компьютеры",
                parent_id=electronics.id,
                is_active=True,
            )

            # Подкатегории смартфонов
            apple_phones = Category(
                id=UUID("123e4567-e89b-12d3-a456-426614174021"),
                name="iPhone",
                slug="iphone",
                description="Apple iPhone",
                parent_id=smartphones.id,
                is_active=True,
            )

            samsung_phones = Category(
                id=UUID("123e4567-e89b-12d3-a456-426614174022"),
                name="Samsung Galaxy",
                slug="samsung-galaxy",
                description="Samsung Galaxy",
                parent_id=smartphones.id,
                is_active=True,
            )

            session.add_all([
                electronics, clothing, home,
                smartphones, laptops, tablets,
                apple_phones, samsung_phones
            ])
            await session.commit()
            print(f"Created categories")

            # ============================================
            # 2. ТОВАРЫ
            # ============================================
            print("\nCreating products...")

            products_data = [
                # iPhone
                {
                    "id": "770e8400-e29b-41d4-a716-446655440001",
                    "slug": "iphone-14-pro",
                    "title": "iPhone 14 Pro",
                    "description": "Смартфон Apple iPhone 14 Pro с диагональю 6.1 дюйма, процессором A16 Bionic и профессиональной камерой",
                    "category_id": apple_phones.id,
                    "status": ProductStatus.MODERATED,
                    "images": [
                        {"url": "https://example.com/images/iphone14_pro_1.jpg", "order": 1},
                        {"url": "https://example.com/images/iphone14_pro_2.jpg", "order": 2},
                        {"url": "https://example.com/images/iphone14_pro_3.jpg", "order": 3},
                    ],
                    "characteristics": [
                        {"name": "BRAND", "value": "Apple"},
                        {"name": "OS", "value": "iOS"},
                        {"name": "SCREEN_SIZE", "value": "6.1\""},
                    ],
                    "skus": [
                        {
                            "name": "iPhone 14 Pro 128GB Silver",
                            "price": 99990.00,
                            "quantity": 15,
                            "characteristics": [
                                {"name": "MEMORY", "value": "128GB"},
                                {"name": "COLOR", "value": "Silver"},
                            ],
                            "images": [
                                {"url": "https://example.com/images/iphone14_silver.jpg", "order": 1},
                            ]
                        },
                        {
                            "name": "iPhone 14 Pro 256GB Gold",
                            "price": 109990.00,
                            "quantity": 10,
                            "characteristics": [
                                {"name": "MEMORY", "value": "256GB"},
                                {"name": "COLOR", "value": "Gold"},
                            ],
                            "images": [
                                {"url": "https://example.com/images/iphone14_gold.jpg", "order": 1},
                            ]
                        },
                        {
                            "name": "iPhone 14 Pro 512GB Space Black",
                            "price": 129990.00,
                            "quantity": 5,
                            "characteristics": [
                                {"name": "MEMORY", "value": "512GB"},
                                {"name": "COLOR", "value": "Space Black"},
                            ],
                            "images": [
                                {"url": "https://example.com/images/iphone14_black.jpg", "order": 1},
                            ]
                        },
                    ]
                },
                {
                    "id": "770e8400-e29b-41d4-a716-446655440002",
                    "slug": "iphone-15-pro-max",
                    "title": "iPhone 15 Pro Max",
                    "description": "Флагманский смартфон Apple с титановым корпусом, процессором A17 Pro и улучшенной камерой",
                    "category_id": apple_phones.id,
                    "status": ProductStatus.MODERATED,
                    "images": [
                        {"url": "https://example.com/images/iphone15_pro_1.jpg", "order": 1},
                        {"url": "https://example.com/images/iphone15_pro_2.jpg", "order": 2},
                    ],
                    "characteristics": [
                        {"name": "BRAND", "value": "Apple"},
                        {"name": "OS", "value": "iOS"},
                        {"name": "SCREEN_SIZE", "value": "6.7\""},
                        {"name": "MATERIAL", "value": "Titanium"},
                    ],
                    "skus": [
                        {
                            "name": "iPhone 15 Pro Max 256GB Natural Titanium",
                            "price": 139990.00,
                            "quantity": 8,
                            "characteristics": [
                                {"name": "MEMORY", "value": "256GB"},
                                {"name": "COLOR", "value": "Natural Titanium"},
                            ],
                            "images": []
                        },
                        {
                            "name": "iPhone 15 Pro Max 512GB Blue Titanium",
                            "price": 159990.00,
                            "quantity": 5,
                            "characteristics": [
                                {"name": "MEMORY", "value": "512GB"},
                                {"name": "COLOR", "value": "Blue Titanium"},
                            ],
                            "images": []
                        },
                    ]
                },
                # Samsung
                {
                    "id": "770e8400-e29b-41d4-a716-446655440003",
                    "slug": "samsung-galaxy-s24-ultra",
                    "title": "Samsung Galaxy S24 Ultra",
                    "description": "Флагманский смартфон Samsung с S Pen, процессором Snapdragon 8 Gen 3 и AI-функциями",
                    "category_id": samsung_phones.id,
                    "status": ProductStatus.MODERATED,
                    "images": [
                        {"url": "https://example.com/images/s24_ultra_1.jpg", "order": 1},
                        {"url": "https://example.com/images/s24_ultra_2.jpg", "order": 2},
                    ],
                    "characteristics": [
                        {"name": "BRAND", "value": "Samsung"},
                        {"name": "OS", "value": "Android"},
                        {"name": "SCREEN_SIZE", "value": "6.8\""},
                        {"name": "S_PEN", "value": "Yes"},
                    ],
                    "skus": [
                        {
                            "name": "Samsung Galaxy S24 Ultra 256GB Titanium Gray",
                            "price": 119990.00,
                            "quantity": 12,
                            "characteristics": [
                                {"name": "MEMORY", "value": "256GB"},
                                {"name": "COLOR", "value": "Titanium Gray"},
                            ],
                            "images": []
                        },
                        {
                            "name": "Samsung Galaxy S24 Ultra 512GB Titanium Black",
                            "price": 139990.00,
                            "quantity": 7,
                            "characteristics": [
                                {"name": "MEMORY", "value": "512GB"},
                                {"name": "COLOR", "value": "Titanium Black"},
                            ],
                            "images": []
                        },
                    ]
                },
                # MacBook
                {
                    "id": "770e8400-e29b-41d4-a716-446655440004",
                    "slug": "macbook-pro-14-m3",
                    "title": "MacBook Pro 14\" M3",
                    "description": "Профессиональный ноутбук Apple с чипом M3, дисплеем Liquid Retina XDR",
                    "category_id": laptops.id,
                    "status": ProductStatus.MODERATED,
                    "images": [
                        {"url": "https://example.com/images/macbook_pro_14_1.jpg", "order": 1},
                        {"url": "https://example.com/images/macbook_pro_14_2.jpg", "order": 2},
                    ],
                    "characteristics": [
                        {"name": "BRAND", "value": "Apple"},
                        {"name": "OS", "value": "macOS"},
                        {"name": "SCREEN_SIZE", "value": "14.2\""},
                        {"name": "PROCESSOR", "value": "Apple M3"},
                    ],
                    "skus": [
                        {
                            "name": "MacBook Pro 14 M3 8GB 512GB Space Gray",
                            "price": 179990.00,
                            "quantity": 6,
                            "characteristics": [
                                {"name": "RAM", "value": "8GB"},
                                {"name": "SSD", "value": "512GB"},
                                {"name": "COLOR", "value": "Space Gray"},
                            ],
                            "images": []
                        },
                        {
                            "name": "MacBook Pro 14 M3 Pro 18GB 512GB Silver",
                            "price": 229990.00,
                            "quantity": 4,
                            "characteristics": [
                                {"name": "RAM", "value": "18GB"},
                                {"name": "SSD", "value": "512GB"},
                                {"name": "COLOR", "value": "Silver"},
                            ],
                            "images": []
                        },
                    ]
                },
            ]

            created_products = []
            for prod_data in products_data:
                product = Product(
                    id=UUID(prod_data["id"]),
                    slug=prod_data["slug"],
                    title=prod_data["title"],
                    description=prod_data["description"],
                    category_id=prod_data["category_id"],
                    status=prod_data["status"],
                )

                # Добавляем изображения товара
                for img_data in prod_data.get("images", []):
                    product.images.append(ProductImage(
                        url=img_data["url"],
                        order=img_data["order"],
                    ))

                # Добавляем характеристики товара
                for char_data in prod_data.get("characteristics", []):
                    product.characteristics.append(ProductCharacteristic(
                        name=char_data["name"],
                        value=char_data["value"],
                    ))

                # Добавляем SKU
                for sku_data in prod_data.get("skus", []):
                    sku = Sku(
                        name=sku_data["name"],
                        price=sku_data["price"],
                        quantity=sku_data["quantity"],
                    )

                    # Характеристики SKU
                    for char_data in sku_data.get("characteristics", []):
                        sku.characteristics.append(SkuCharacteristic(
                            name=char_data["name"],
                            value=char_data["value"],
                        ))

                    # Изображения SKU
                    for img_data in sku_data.get("images", []):
                        sku.images.append(SkuImage(
                            url=img_data["url"],
                            order=img_data["order"],
                        ))

                    product.skus.append(sku)

                session.add(product)
                created_products.append(product)

            await session.commit()
            print(f"Created products")

            print("\nSeed data created successfully!")

    except Exception as e:
        print(f"\nError creating seed data: {e}")
        import traceback
        traceback.print_exc()
        await session.rollback()
        raise
    finally:
        await engine.dispose()


async def clear_data():
    """Очистить все данные (для повторного запуска)"""

    print("🗑️  Clearing existing data...")

    engine = create_async_engine(DB_CONFIG.get_url(is_async=True))
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Очищаем в правильном порядке (из-за foreign keys)
            await session.execute(text("DELETE FROM sku_characteristics"))
            await session.execute(text("DELETE FROM sku_images"))
            await session.execute(text("DELETE FROM skus"))
            await session.execute(text("DELETE FROM product_characteristics"))
            await session.execute(text("DELETE FROM product_images"))
            await session.execute(text("DELETE FROM products"))
            await session.execute(text("DELETE FROM categories"))
            await session.execute(text("DELETE FROM alembic_version"))

            await session.commit()
            print("✅ Data cleared successfully")

    except Exception as e:
        print(f"❌ Error clearing data: {e}")
        await session.rollback()
        raise
    finally:
        await engine.dispose()


async def main():
    """Главная функция"""

    import argparse

    parser = argparse.ArgumentParser(description="Seed data for marketplace")
    parser.add_argument("--clear", action="store_true", help="Clear all data before seeding")
    parser.add_argument("--only-clear", action="store_true", help="Only clear data, don't seed")
    args = parser.parse_args()

    if args.only_clear:
        await clear_data()
        return

    if args.clear:
        await clear_data()
        print("\n⏳ Waiting 2 seconds before seeding...")
        await asyncio.sleep(2)

    await seed_data()


if __name__ == "__main__":
    asyncio.run(main())