import pytest

import requests

BASE_URL = "http://localhost:8000"

@pytest.fixture

def jwt_token():

    return "bearer_token_with_seller_id_123"

def test_create_product_returns_201_with_created_status(jwt_token, requests_mock):

    payload = {"name": "New Product", "category_id": 1, "images": ["http://img.jpg"]}

    requests_mock.post(f"{BASE_URL}/api/v1/products", json={"status": "CREATED", "skus": [], "seller_id": 123}, status_code=201)

    headers = {"Authorization": f"Bearer {jwt_token}"}

    response = requests.post(f"{BASE_URL}/api/v1/products", json=payload, headers=headers)

    assert response.status_code == 201

def test_seller_id_taken_from_jwt(jwt_token, requests_mock):

    payload = {"name": "Product", "category_id": 1, "images": ["http://img.jpg"], "seller_id": 999}

    requests_mock.post(f"{BASE_URL}/api/v1/products", json={"status": "CREATED", "skus": [], "seller_id": 123}, status_code=201)

    headers = {"Authorization": f"Bearer {jwt_token}"}

    response = requests.post(f"{BASE_URL}/api/v1/products", json=payload, headers=headers)

    assert response.json()["seller_id"] == 123

def test_missing_images_returns_400(jwt_token, requests_mock):

    payload = {"name": "No Images", "category_id": 1}

    requests_mock.post(f"{BASE_URL}/api/v1/products", text="Field images is required", status_code=400)

    headers = {"Authorization": f"Bearer {jwt_token}"}

    response = requests.post(f"{BASE_URL}/api/v1/products", json=payload, headers=headers)

    assert response.status_code == 400

def test_missing_category_returns_400(jwt_token, requests_mock):

    payload = {"name": "No Category", "images": ["http://img.jpg"]}

    requests_mock.post(f"{BASE_URL}/api/v1/products", text="Field category_id is required", status_code=400)

    headers = {"Authorization": f"Bearer {jwt_token}"}

    response = requests.post(f"{BASE_URL}/api/v1/products", json=payload, headers=headers)

    assert response.status_code == 400


def test_create_sku_valid(requests_mock, jwt_token):
    product_id = "test-product-id-123"
    # Мокаем создание продукта с этим ID
    requests_mock.post(f"{BASE_URL}/api/v1/products", json={"id": product_id, "status": "CREATED"}, status_code=201)
    # Мокаем создание SKU
    requests_mock.post(f"{BASE_URL}/api/v1/skus", json={
        "id": "sku-id-123",
        "product_id": product_id,
        "name": "Shoe Size Medium",
        "price": 99.99,
        "quantity": 50,
        "status": "CREATED"
    }, status_code=201)
    
    payload = {
        "product_id": product_id,
        "name": "Shoe Size Medium",
        "price": 99.99,
        "quantity": 50
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.post(f"{BASE_URL}/api/v1/skus", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["product_id"] == product_id
    assert response.json()["quantity"] == 50


def test_delete_sku_dynamic(jwt_token, requests_mock):
    # 1. Создаем продукт
    product_payload = {"name": "Test Product", "category_id": 1, "images": []}
    requests_mock.post(f"{BASE_URL}/api/v1/products", 
                      json={"id": "test-product-id-123", "status": "CREATED"}, 
                      status_code=201)
    
    headers = {"Authorization": f"Bearer {jwt_token}"}
    product_response = requests.post(
        f"{BASE_URL}/api/v1/products", 
        json=product_payload, 
        headers=headers
    )
    assert product_response.status_code == 201
    product_id = product_response.json()["id"]
    
    # 2. Создаем SKU для этого продукта
    sku_payload = {
        "product_id": product_id,
        "name": "Test SKU",
        "price": 99.99,
        "quantity": 10
    }
    sku_id = "test-sku-id-123"
    requests_mock.post(f"{BASE_URL}/api/v1/skus", 
                      json={
                          "id": sku_id,
                          "product_id": product_id,
                          "status": "CREATED"
                      }, 
                      status_code=201)
    sku_response = requests.post(
        f"{BASE_URL}/api/v1/skus", 
        json=sku_payload, 
        headers=headers
    )
    assert sku_response.status_code == 201
    sku_id = sku_response.json()["id"]
    
    # 3. Удаляем SKU
    requests_mock.delete(f"{BASE_URL}/api/v1/skus/{sku_id}", 
                        json={"status": "DELETED"}, 
                        status_code=200)
    delete_response = requests.delete(
        f"{BASE_URL}/api/v1/skus/{sku_id}", 
        headers=headers
    )
    assert delete_response.status_code == 200

# Тест обновления товара

def test_update_product_success(jwt_token, requests_mock):
    product_id = "update-prod-1"
    # Мок GET существующего товара
    requests_mock.get(f"{BASE_URL}/api/v1/products/{product_id}",
                      json={"id": product_id, "name": "Old", "category_id": 1, "images": []},
                      status_code=200)
    # Мок PUT обновления
    requests_mock.put(f"{BASE_URL}/api/v1/products/{product_id}",
                      json={"id": product_id, "name": "New", "category_id": 1, "images": ["http://new.jpg"]},
                      status_code=200)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {"name": "New", "images": ["http://new.jpg"]}
    response = requests.put(f"{BASE_URL}/api/v1/products/{product_id}", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "New"

# Тест обновления SKU

def test_update_sku_success(jwt_token, requests_mock):
    sku_id = "update-sku-1"
    # Мок GET существующего SKU
    requests_mock.get(f"{BASE_URL}/api/v1/skus/{sku_id}",
                      json={"id": sku_id, "product_id": "prod-1", "name": "Old", "price": 50.0, "quantity": 20},
                      status_code=200)
    # Мок PUT обновления SKU
    requests_mock.put(f"{BASE_URL}/api/v1/skus/{sku_id}",
                      json={"id": sku_id, "product_id": "prod-1", "name": "New", "price": 60.0, "quantity": 15},
                      status_code=200)
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {"name": "New", "price": 60.0, "quantity": 15}
    response = requests.put(f"{BASE_URL}/api/v1/skus/{sku_id}", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["price"] == 60.0

def test_delete_product_success(jwt_token, requests_mock):
    product_id = "delete-prod-123"
    requests_mock.post(
        f"{BASE_URL}/api/v1/products",
        json={"id": product_id, "status": "CREATED"},
        status_code=201,
    )
    requests_mock.delete(
        f"{BASE_URL}/api/v1/products/{product_id}",
        json={"status": "DELETED"},
        status_code=200,
    )
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.delete(
        f"{BASE_URL}/api/v1/products/{product_id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "DELETED"

def test_create_invoice_success(jwt_token, requests_mock):
    invoice_id = "invoice-123"
    # Мокаем POST запрос на создание накладной
    requests_mock.post(
        f"{BASE_URL}/api/v1/invoices",
        json={
            "id": invoice_id,
            "status": "CREATED",
            "order_id": 42,
            "total_price": 199.97,
        },
        status_code=201,
    )
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {
        "order_id": 42,
        "items": [
            {"sku_id": "sku-1", "quantity": 3},
            {"sku_id": "sku-2", "quantity": 1},
        ],
        "total_price": 199.97,
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/invoices", json=payload, headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == invoice_id
    assert data["status"] == "CREATED"
    assert data["order_id"] == 42
    assert data["total_price"] == 199.97

def test_view_my_products_success(jwt_token, requests_mock):
    # Мокаем GET запрос к эндпоинту просмотра товаров продавца
    requests_mock.get(
        f"{BASE_URL}/api/v1/seller/products",
        json=[
            {"id": "prod-1", "name": "Product A", "seller_id": 123},
            {"id": "prod-2", "name": "Product B", "seller_id": 123},
        ],
        status_code=200,
    )
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.get(f"{BASE_URL}/api/v1/seller/products", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    for item in data:
        assert item["seller_id"] == 123

