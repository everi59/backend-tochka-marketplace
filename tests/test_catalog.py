import pytest
from unittest.mock import Mock, patch

# Эмуляция ответа от сервера для каталога
@pytest.fixture
def mock_catalog_response():
    return {
        "products": [
            {"id": 1, "name": "iPhone 15 Pro", "category": "Smartphones", "price": 95000, "brand": "Apple"},
            {"id": 2, "name": "Samsung Galaxy S23", "category": "Smartphones", "price": 75000, "brand": "Samsung"},
            {"id": 3, "name": "Xiaomi 13 Ultra", "category": "Smartphones", "price": 65000, "brand": "Xiaomi"}
        ],
        "facets": {
            "brands": {"Apple": 1, "Samsung": 1, "Xiaomi": 1},
            "categories": {"Smartphones": 3}
        }
    }

@patch('requests.get')
#US-CAT-01: каталог с фильтрами и фасетами
def test_catalog_filtering_by_brand(mock_get, mock_catalog_response):
    # Настраиваем mock, чтобы он возвращал наш JSON
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_catalog_response

    # Имитируем вызов функции получения и фильтрации товаров в коде приложения
    from catalog_service import get_filtered_products
    filtered_products = get_filtered_products(brand="Apple")

    # Проверяем, что отфильтровался только iPhone
    assert len(filtered_products) == 1
    assert filtered_products[0]["name"] == "iPhone 15 Pro"
    assert filtered_products[0]["brand"] == "Apple"


@patch('requests.get')
#US-CAT-02: текстовый поиск
#товар найден по совпадению
def test_search_product_found(mock_get, mock_catalog_response):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_catalog_response

    from catalog_service import search_products
    results = search_products(query="iPhone")

    assert len(results) == 1
    assert "iPhone" in results[0]["name"]

@patch('requests.get')
def test_search_product_not_found(mock_get):
    # Mock возвращает пустой ответ, имитируя, что ничего не найдено
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"products": [], "facets": {}}

    from catalog_service import search_products
    results = search_products(query="xyz123abc")

    assert len(results) == 0

@patch('requests.get')
#US-CAT-03: карточка товара для покупателя
def test_get_product_card_details(mock_get):
    # Заглушка для конкретной карточки товара
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "id": 1,
        "name": "iPhone 15 Pro",
        "price": 95000,
        "specs": {"RAM": "8GB", "Storage": "128GB"}
    }

    from catalog_service import get_product_by_id
    product = get_product_by_id(product_id=1)

    assert product["name"] == "iPhone 15 Pro"
    assert product["specs"]["RAM"] == "8GB"

@patch('requests.get')
#US-CAT-04: похожие товары (проверка что алгоритм рекомендаций выдает товары из той же категории)
def test_similar_products_recommendation(mock_get, mock_catalog_response):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_catalog_response

    from catalog_service import get_similar_products
    # Запрашиваем похожие для товара с ID=1 (Смартфон)
    similar = get_similar_products(product_id=1)

    # Должны вернуться остальные смартфоны из mock-списка (Samsung и Xiaomi)
    assert len(similar) == 2
    for item in similar:
        assert item["category"] == "Smartphones"

@patch('requests.get')
#US-CAT-05: навигация по категориям (проверка корректности маппинга и построения путей при запросе к структуре категорий)
def test_category_navigation_tree(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "categories": [
            {"id": "appliances", "name": "Бытовая техника", "subs": ["coffee-machines", "microwaves"]}
        ]
    }

    from catalog_service import get_category_path
    path = get_category_path(category_id="coffee-machines")

    assert path == "Главная > Бытовая техника > Кофемашины"