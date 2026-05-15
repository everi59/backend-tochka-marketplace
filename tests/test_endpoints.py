import pytest
from fastapi.testclient import TestClient

# Import FastAPI app
from app.main import app

client = TestClient(app)

# List of endpoints to exercise
ENDPOINTS = [
    "/api/v1/cart/items",
    "/api/v1/cart/cart",
    "/api/v1/favorites",
    "/api/v1/banners",
    "/api/v1/seller/invoices",
    "/api/v1/seller/products",
    "/api/v1/seller/skus",
    "/api/v1/orders/order_items",
    "/api/v1/orders/orders",
    "/api/v1/moderation/reasons",
    "/api/v1/moderation/queue",
    "/api/v1/moderation/decisions",
    "/api/v1/catalog/categories",
    "/api/v1/catalog/breadcrumbs",
    "/api/v1/catalog/products",
    "/api/v1/catalog/facets",
    "/api/v1/collections",
]

# ---------- GET tests ----------

def test_get_endpoints():
    """Проверяем, что каждый эндпоинт отдает 200 или 404.""" 
    for ep in ENDPOINTS:
        print(f"\n---запрашиваем {ep} ---")
        resp = client.get(ep)
        print(f"Статус: {resp.status_code}")
        if resp.status_code >= 400:
            # выводим тело ответа, если статус ≥ 400
            print(f"Тело: {resp.text}")
        assert resp.status_code in (200, 404), f"{ep} returned {resp.status_code}"

# ---------- POST/PUT/DELETE placeholders ----------

# Example POST test – replace body and endpoint with real payloads

def test_post_example():
    # Adjust `/api/v1/seller/products` to a real POST endpoint when available
    resp = client.post("/api/v1/seller/products", json={})
    # When route not implemented, expect 405 or 404; if implemented, check 201/200
    if resp.status_code in (201, 200):
        assert resp.ok
    else:
        assert resp.status_code in (404, 405)

# Example PUT test

def test_put_example():
    resp = client.put("/api/v1/seller/products/1", json={})
    if resp.status_code in (200, 204):
        assert resp.ok
    else:
        assert resp.status_code in (404, 405)

# Example DELETE test

def test_delete_example():
    resp = client.delete("/api/v1/seller/products/1")
    if resp.status_code in (200, 204):
        assert resp.ok
    else:
        assert resp.status_code in (404, 405)

