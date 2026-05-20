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
