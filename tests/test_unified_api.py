from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_b2b_and_b2c_happy_path() -> None:
    with TestClient(app) as client:
        seller_register = client.post(
            "/b2b/api/v1/auth/register",
            json={
                "email": "new-seller@example.com",
                "password": "sellerpass123",
                "first_name": "Neo",
                "last_name": "Seller",
                "company_name": "Neo LLC",
                "inn": "1234567891",
            },
        )
        assert seller_register.status_code == 201
        seller_tokens = seller_register.json()
        seller_headers = {"Authorization": f"Bearer {seller_tokens['access_token']}"}

        category_resp = client.get("/b2b/api/v1/categories")
        assert category_resp.status_code == 200
        category_id = category_resp.json()[0]["id"]

        product_resp = client.post(
            "/b2b/api/v1/products",
            headers=seller_headers,
            json={
                "title": "Neo Phone",
                "description": "Seller side product",
                "category_id": category_id,
            },
        )
        assert product_resp.status_code == 201
        product_id = product_resp.json()["id"]

        sku_resp = client.post(
            "/b2b/api/v1/skus",
            headers=seller_headers,
            json={
                "product_id": product_id,
                "name": "Neo Phone 128GB",
                "price": 2500000,
                "discount": 100000,
                "cost_price": 2000000,
                "article": "NEO-128",
            },
        )
        assert sku_resp.status_code == 201
        sku_id = sku_resp.json()["id"]

        invoice_resp = client.post(
            "/b2b/api/v1/invoices",
            headers=seller_headers,
            json={"items": [{"sku_id": sku_id, "quantity": 5}]},
        )
        assert invoice_resp.status_code == 201
        invoice_id = invoice_resp.json()["id"]

        accept_resp = client.post(
            f"/b2b/api/v1/invoices/{invoice_id}/accept",
            headers=seller_headers,
            json={},
        )
        assert accept_resp.status_code == 200
        assert accept_resp.json()["status"] == "ACCEPTED"

        moderation_resp = client.post(
            "/b2b/api/v1/moderation/events",
            headers={"X-Service-Key": "svc"},
            json={
                "idempotency_key": "6cb24767-8cad-4b82-b7a4-fb33b534ec1c",
                "product_id": product_id,
                "event_type": "MODERATED",
                "occurred_at": "2026-01-01T00:00:00Z",
            },
        )
        assert moderation_resp.status_code == 204

        buyer_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": "buyer@example.com",
                "password": "buyerpass123",
                "first_name": "Neo",
            },
        )
        assert buyer_register.status_code == 201
        buyer_tokens = buyer_register.json()
        buyer_headers = {"Authorization": f"Bearer {buyer_tokens['access_token']}"}

        address_resp = client.post(
            "/api/v1/buyers/me/addresses",
            headers=buyer_headers,
            json={
                "country": "RU",
                "city": "Ekaterinburg",
                "street": "Lenina",
                "building": "1",
            },
        )
        assert address_resp.status_code == 201
        address_id = address_resp.json()["id"]

        payment_resp = client.post(
            "/api/v1/buyers/me/payment-methods",
            headers=buyer_headers,
            json={"type": "CARD", "card_last4": "4242", "card_brand": "VISA"},
        )
        assert payment_resp.status_code == 201
        payment_id = payment_resp.json()["id"]

        catalog_resp = client.get("/api/v1/catalog/products")
        assert catalog_resp.status_code == 200
        assert any(item["id"] == product_id for item in catalog_resp.json()["items"])

        add_cart = client.post(
            "/api/v1/cart/items",
            headers=buyer_headers,
            json={"sku_id": sku_id, "quantity": 1},
        )
        assert add_cart.status_code == 200
        assert add_cart.json()["items_count"] == 1

        order_resp = client.post(
            "/api/v1/orders",
            headers={**buyer_headers, "Idempotency-Key": "0fa92fa8-81bb-4f4b-92cf-c7d76668475f"},
            json={"address_id": address_id, "payment_method_id": payment_id},
        )
        assert order_resp.status_code == 201
        assert order_resp.json()["status"] == "PAID"


def test_guest_cart_merge_and_b2b_event() -> None:
    with TestClient(app) as client:
        catalog = client.get("/api/v1/catalog/products").json()
        product = catalog["items"][0]
        detail = client.get(f"/api/v1/catalog/products/{product['id']}").json()
        sku_id = detail["skus"][0]["id"]

        session_id = "c59c2c75-1e5c-4e5c-97b2-b2dd3414d842"
        guest_cart = client.post(
            "/api/v1/cart/items",
            headers={"X-Session-Id": session_id},
            json={"sku_id": sku_id, "quantity": 1},
        )
        assert guest_cart.status_code == 200

        buyer_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": "merge-buyer@example.com",
                "password": "buyerpass123",
                "first_name": "Merge",
            },
        )
        buyer_tokens = buyer_register.json()

        merged = client.post(
            "/api/v1/auth/login",
            headers={"X-Session-Id": session_id},
            json={"email": "merge-buyer@example.com", "password": "buyerpass123"},
        )
        assert merged.status_code == 200
        buyer_headers = {"Authorization": f"Bearer {buyer_tokens['access_token']}"}
        cart_after = client.get("/api/v1/cart", headers=buyer_headers)
        assert cart_after.status_code == 200
        assert cart_after.json()["items_count"] == 1

        subscribe = client.post(
            f"/api/v1/favorites/{product['id']}/subscribe",
            headers=buyer_headers,
            json={"events": ["PRICE_DROP"]},
        )
        assert subscribe.status_code == 204

        event_resp = client.post(
            "/api/v1/b2b/events",
            headers={"X-Service-Key": "svc"},
            json={
                "event_type": "PRICE_CHANGED",
                "idempotency_key": "4edfe434-d6c0-43b5-8068-8f0a1db7b883",
                "occurred_at": "2026-01-01T00:00:00Z",
                "payload": {
                    "sku_id": sku_id,
                    "product_id": product["id"],
                    "old_price": 9999000,
                    "new_price": 8999000,
                },
            },
        )
        assert event_resp.status_code == 202

        notifications = client.get("/api/v1/notifications", headers=buyer_headers)
        assert notifications.status_code == 200
        assert notifications.json()["total_count"] >= 1
