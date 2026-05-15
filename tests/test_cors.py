import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test CORS preflight response

def test_cors_preflight():
    """Проверяем наличие CORS-заголовков для OPTIONS-запроса."""
    print("\n=== проверяем CORS-префлайт для /api/v1/catalog/categories ===")
    response = client.options(
        "/api/v1/categories",  # any route
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    print(f": {response.status_code}")
    print(f"Allow-origin: {response.headers.get('access-control-allow-origin')}")
    print(f"Allow-methods: {response.headers.get('access-control-allow-methods')}")
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "GET" in response.headers["access-control-allow-methods"]
