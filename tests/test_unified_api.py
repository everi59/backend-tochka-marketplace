from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app.main import app


def _product_images() -> list[dict[str, object]]:
    return [{"url": "https://example.com/product.jpg", "ordering": 0}]


def _sku_payload(product_id: str, name: str, price: int, article: str) -> dict[str, object]:
    return {
        "product_id": product_id,
        "name": name,
        "price": price,
        "cost_price": max(price // 2, 1),
        "article": article,
        "images": [{"url": "https://example.com/sku.jpg", "ordering": 0}],
    }


def _create_seller(client: TestClient, email: str, inn: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "sellerpass123",
            "first_name": "Neo",
            "last_name": "Seller",
            "company_name": "Neo LLC",
            "inn": inn,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _create_buyer(client: TestClient, email: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "buyerpass123",
            "first_name": "Neo",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_b2b_and_b2c_happy_path() -> None:
    with TestClient(app) as client:
        seller_tokens = _create_seller(client, "new-seller@example.com", "1234567891")
        seller_headers = {"Authorization": f"Bearer {seller_tokens['access_token']}"}

        category_id = client.get("/api/v1/categories").json()[0]["id"]
        product_resp = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={
                "title": "Neo Phone",
                "description": "Seller side product",
                "category_id": category_id,
                "images": _product_images(),
            },
        )
        assert product_resp.status_code == 201
        product_id = product_resp.json()["id"]

        sku_resp = client.post(
            "/api/v1/skus",
            headers=seller_headers,
            json={
                "product_id": product_id,
                "name": "Neo Phone 128GB",
                "price": 2500000,
                "discount": 100000,
                "cost_price": 2000000,
                "article": "NEO-128",
                "images": [{"url": "https://example.com/neo-sku.jpg", "ordering": 0}],
            },
        )
        assert sku_resp.status_code == 201
        sku_id = sku_resp.json()["id"]

        moderation_resp = client.post(
            "/api/v1/moderation/events",
            headers={"X-Service-Key": "svc"},
            json={
                "idempotency_key": "6cb24767-8cad-4b82-b7a4-fb33b534ec1c",
                "product_id": product_id,
                "event_type": "MODERATED",
                "occurred_at": "2026-01-01T00:00:00Z",
            },
        )
        assert moderation_resp.status_code == 204

        invoice_resp = client.post(
            "/api/v1/invoices",
            headers=seller_headers,
            json={"items": [{"sku_id": sku_id, "quantity": 5}]},
        )
        assert invoice_resp.status_code == 201
        invoice_id = invoice_resp.json()["id"]

        accept_resp = client.post(
            f"/api/v1/invoices/{invoice_id}/accept",
            headers=seller_headers,
            json={},
        )
        assert accept_resp.status_code == 200
        assert accept_resp.json()["status"] == "ACCEPTED"

        buyer_tokens = _create_buyer(client, "buyer@example.com")
        buyer_headers = {"Authorization": f"Bearer {buyer_tokens['access_token']}"}

        address_id = client.post(
            "/api/v1/buyers/me/addresses",
            headers=buyer_headers,
            json={
                "country": "RU",
                "city": "Ekaterinburg",
                "street": "Lenina",
                "building": "1",
            },
        ).json()["id"]
        payment_id = client.post(
            "/api/v1/buyers/me/payment-methods",
            headers=buyer_headers,
            json={"type": "CARD", "card_last4": "4242", "card_brand": "VISA"},
        ).json()["id"]

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

        _create_buyer(client, "merge-buyer@example.com")
        merged = client.post(
            "/api/v1/auth/login",
            headers={"X-Session-Id": session_id},
            json={"email": "merge-buyer@example.com", "password": "buyerpass123"},
        )
        assert merged.status_code == 200
        buyer_headers = {"Authorization": f"Bearer {merged.json()['access_token']}"}

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
            "/api/v1/events/b2b",
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


def test_order_cancel_assembling_and_sets_pending_on_http_failure() -> None:
    with TestClient(app) as client:
        seller_tokens = _create_seller(client, "cancel-seller@example.com", "1234567892")
        seller_headers = {"Authorization": f"Bearer {seller_tokens['access_token']}"}
        category_id = client.get("/api/v1/categories").json()[0]["id"]
        product_id = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={
                "title": "Cancel Phone",
                "description": "Test",
                "category_id": category_id,
                "images": _product_images(),
            },
        ).json()["id"]
        sku_id = client.post(
            "/api/v1/skus",
            headers=seller_headers,
            json=_sku_payload(product_id, "Cancel SKU", 1000, "CANCEL-1"),
        ).json()["id"]
        client.post(
            "/api/v1/moderation/events",
            headers={"X-Service-Key": "svc"},
            json={
                "idempotency_key": "cancel-1",
                "product_id": product_id,
                "event_type": "MODERATED",
                "occurred_at": "2026-01-01T00:00:00Z",
            },
        )

        buyer_tokens = _create_buyer(client, "cancel-buyer@example.com")
        buyer_headers = {"Authorization": f"Bearer {buyer_tokens['access_token']}"}
        address_id = client.post(
            "/api/v1/buyers/me/addresses",
            headers=buyer_headers,
            json={"country": "RU", "city": "Ekaterinburg", "street": "Lenina", "building": "1"},
        ).json()["id"]
        payment_id = client.post(
            "/api/v1/buyers/me/payment-methods",
            headers=buyer_headers,
            json={"type": "CARD", "card_last4": "4242", "card_brand": "VISA"},
        ).json()["id"]
        client.post("/api/v1/cart/items", headers=buyer_headers, json={"sku_id": sku_id, "quantity": 1})
        order = client.post(
            "/api/v1/orders",
            headers={**buyer_headers, "Idempotency-Key": "cancel-order-1"},
            json={"address_id": address_id, "payment_method_id": payment_id},
        ).json()

        app.state.store.orders[order["id"]]["status"] = "ASSEMBLING"
        assembling_cancel = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=buyer_headers, json={"reason": "x"})
        assert assembling_cancel.status_code == 200
        assert assembling_cancel.json()["status"] == "CANCELLED"

        app.state.store.orders[order["id"]]["status"] = "PAID"
        with patch("app.core.services.commerce.httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ConnectTimeout("boom"))):
            pending_cancel = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=buyer_headers, json={"reason": "x"})

        assert pending_cancel.status_code == 200
        assert pending_cancel.json()["status"] == "CANCEL_PENDING"


def test_favorites_filter_out_invisible_products() -> None:
    with TestClient(app) as client:
        buyer_tokens = _create_buyer(client, "fav-buyer@example.com")
        buyer_headers = {"Authorization": f"Bearer {buyer_tokens['access_token']}"}
        product_id = next(iter(app.state.store.public_product_ids()))
        client.put(f"/api/v1/favorites/{product_id}", headers=buyer_headers)
        client.post(
            "/api/v1/moderation/events",
            headers={"X-Service-Key": "svc"},
            json={
                "event_type": "PRODUCT_BLOCKED",
                "idempotency_key": "fav-1",
                "occurred_at": "2026-01-01T00:00:00Z",
                "payload": {"product_id": product_id},
            },
        )
        favorites = client.get("/api/v1/favorites", headers=buyer_headers)
        assert favorites.status_code == 200
        assert favorites.json()["total_count"] == 0


def test_cart_marks_blocked_items_unavailable_and_excludes_from_subtotal() -> None:
    with TestClient(app) as client:
        buyer_tokens = _create_buyer(client, "cart-buyer@example.com")
        buyer_headers = {"Authorization": f"Bearer {buyer_tokens['access_token']}"}
        detail = client.get(f"/api/v1/catalog/products/{next(iter(app.state.store.public_product_ids()))}").json()
        sku_id = detail["skus"][0]["id"]
        client.post("/api/v1/cart/items", headers=buyer_headers, json={"sku_id": sku_id, "quantity": 1})
        client.post(
            "/api/v1/events/b2b",
            headers={"X-Service-Key": "svc"},
            json={
                "event_type": "PRODUCT_BLOCKED",
                "idempotency_key": "cart-1",
                "occurred_at": "2026-01-01T00:00:00Z",
                "payload": {"product_id": detail["id"]},
            },
        )
        cart = client.get("/api/v1/cart", headers=buyer_headers)
        assert cart.status_code == 200
        assert cart.json()["subtotal"] == 0
        assert cart.json()["items"][0]["available"] is False
        assert cart.json()["items"][0]["unavailable_reason"] == "blocked"
        assert cart.json()["items"][0]["is_available"] is False


def test_catalog_facets_and_invalid_sort() -> None:
    with TestClient(app) as client:
        invalid = client.get("/api/v1/catalog/products?sort=zzz")
        assert invalid.status_code == 400
        product = client.get("/api/v1/catalog/products").json()["items"][0]
        facets = client.get(f"/api/v1/catalog/facets?category_id={product['category_id']}")
        assert facets.status_code == 200
        assert "facets" in facets.json()


def test_public_catalog_requires_service_key_and_short_response() -> None:
    with TestClient(app) as client:
        missing = client.get("/api/v1/public/products")
        assert missing.status_code == 401

        valid = client.get("/api/v1/public/products", headers={"X-Service-Key": "svc"})
        assert valid.status_code == 200
        item = valid.json()["items"][0]
        assert {"title", "slug", "status", "category_id", "created_at", "min_price"}.issubset(item.keys())

        seller_tokens = _create_seller(client, "public-catalog-seller@example.com", "1234567898")
        seller_headers = {"Authorization": f"Bearer {seller_tokens['access_token']}"}
        product1 = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={
                "title": "Public One",
                "description": "First public product",
                "category_id": item["category_id"],
                "images": _product_images(),
            },
        ).json()["id"]
        sku1 = client.post(
            "/api/v1/skus",
            headers=seller_headers,
            json=_sku_payload(product1, "Sku 1", 1000, "PUB-1"),
        ).json()["id"]
        client.post(
            "/api/v1/moderation/events",
            headers={"X-Service-Key": "svc"},
            json={
                "idempotency_key": "public-1",
                "product_id": product1,
                "event_type": "MODERATED",
                "occurred_at": "2026-01-01T00:00:00Z",
            },
        )
        app.state.store.skus[sku1]["stock_quantity"] = 5

        product2 = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={
                "title": "Public Two",
                "description": "Second public product",
                "category_id": item["category_id"],
                "images": _product_images(),
            },
        ).json()["id"]
        sku2 = client.post(
            "/api/v1/skus",
            headers=seller_headers,
            json=_sku_payload(product2, "Sku 2", 2000, "PUB-2"),
        ).json()["id"]
        client.post(
            "/api/v1/moderation/events",
            headers={"X-Service-Key": "svc"},
            json={
                "idempotency_key": "public-2",
                "product_id": product2,
                "event_type": "MODERATED",
                "occurred_at": "2026-01-01T00:00:00Z",
            },
        )
        app.state.store.skus[sku2]["stock_quantity"] = 5

        similar = client.get(f"/api/v1/public/products/{item['id']}/similar", headers={"X-Service-Key": "svc"})
        assert similar.status_code == 200
        similar_item = similar.json()[0]
        assert "title" in similar_item
        assert "category_id" in similar_item


def test_invoice_validation_checks_status_owner_and_empty_items() -> None:
    with TestClient(app) as client:
        seller_tokens = _create_seller(client, "invoice-seller@example.com", "1234567893")
        seller_headers = {"Authorization": f"Bearer {seller_tokens['access_token']}"}
        category_id = client.get("/api/v1/categories").json()[0]["id"]
        product_id = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={
                "title": "Invoice Phone",
                "description": "Test",
                "category_id": category_id,
                "images": _product_images(),
            },
        ).json()["id"]
        sku_id = client.post(
            "/api/v1/skus",
            headers=seller_headers,
            json=_sku_payload(product_id, "Invoice SKU", 1000, "INV-1"),
        ).json()["id"]
        empty = client.post("/api/v1/invoices", headers=seller_headers, json={"items": []})
        assert empty.status_code == 400
        moderated = client.post("/api/v1/invoices", headers=seller_headers, json={"items": [{"sku_id": sku_id, "quantity": 1}]})
        assert moderated.status_code == 400

        other_tokens = _create_seller(client, "other-invoice@example.com", "1234567894")
        other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}
        forbidden = client.post("/api/v1/invoices", headers=other_headers, json={"items": [{"sku_id": sku_id, "quantity": 1}]})
        assert forbidden.status_code == 404


def test_sku_delete_rules_and_events() -> None:
    with TestClient(app) as client:
        seller_tokens = _create_seller(client, "sku-seller@example.com", "1234567895")
        seller_headers = {"Authorization": f"Bearer {seller_tokens['access_token']}"}
        category_id = client.get("/api/v1/categories").json()[0]["id"]
        product_id = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={
                "title": "Sku Phone",
                "description": "Test",
                "category_id": category_id,
                "images": _product_images(),
            },
        ).json()["id"]
        sku_id = client.post(
            "/api/v1/skus",
            headers=seller_headers,
            json=_sku_payload(product_id, "Sku One", 1000, "SKU-1"),
        ).json()["id"]
        app.state.store.products[product_id]["status"] = "HARD_BLOCKED"
        blocked = client.delete(f"/api/v1/skus/{sku_id}", headers=seller_headers)
        assert blocked.status_code == 403

        app.state.store.products[product_id]["status"] = "ON_MODERATION"
        app.state.store.skus[sku_id]["reserved_quantity"] = 0
        deleted = client.delete(f"/api/v1/skus/{sku_id}", headers=seller_headers)
        assert deleted.status_code == 204
        assert app.state.store.products[product_id]["status"] == "CREATED"
        assert app.state.store.moderation_events[-1]["event_type"] == "PRODUCT_DELETED"
        assert all(event["event_type"] != "SKU_OUT_OF_STOCK" for event in app.state.store.b2b_events)

        product2_id = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={
                "title": "Sku Phone 2",
                "description": "Test",
                "category_id": category_id,
                "images": _product_images(),
            },
        ).json()["id"]
        sku2_id = client.post(
            "/api/v1/skus",
            headers=seller_headers,
            json=_sku_payload(product2_id, "Sku Two", 2000, "SKU-2"),
        ).json()["id"]
        app.state.store.products[product2_id]["status"] = "MODERATED"
        app.state.store.skus[sku2_id]["stock_quantity"] = 5
        out_of_stock = client.delete(f"/api/v1/skus/{sku2_id}", headers=seller_headers)
        assert out_of_stock.status_code == 204
        assert app.state.store.b2b_events[-1]["event_type"] == "SKU_OUT_OF_STOCK"


def test_product_delete_emits_events_and_is_idempotent() -> None:
    with TestClient(app) as client:
        seller_tokens = _create_seller(client, "delete-seller@example.com", "1234567896")
        seller_headers = {"Authorization": f"Bearer {seller_tokens['access_token']}"}
        category_id = client.get("/api/v1/categories").json()[0]["id"]
        product_id = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={
                "title": "Delete Phone",
                "description": "Test",
                "category_id": category_id,
                "images": _product_images(),
            },
        ).json()["id"]
        deleted = client.delete(f"/api/v1/products/{product_id}", headers=seller_headers)
        assert deleted.status_code == 204
        assert app.state.store.products[product_id]["deleted"] is True
        assert app.state.store.moderation_events[-1]["event_type"] == "PRODUCT_DELETED"
        assert app.state.store.b2b_events[-1]["event_type"] == "PRODUCT_DELETED"

        repeat = client.delete(f"/api/v1/products/{product_id}", headers=seller_headers)
        assert repeat.status_code == 400


def test_b2b_create_product_validates_required_slug_uniqueness_and_created_status() -> None:
    with TestClient(app) as client:
        seller_tokens = _create_seller(client, "create-product-seller@example.com", "1234567897")
        seller_headers = {"Authorization": f"Bearer {seller_tokens['access_token']}"}
        category_id = client.get("/api/v1/categories").json()[0]["id"]

        missing_title = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={"description": "Missing title", "category_id": category_id},
        )
        assert missing_title.status_code == 422
        assert "code" in missing_title.json()
        assert "message" in missing_title.json()

        no_images = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={
                "title": "No Images Product",
                "description": "Optional images",
                "category_id": category_id,
            },
        )
        assert no_images.status_code == 201
        assert no_images.json()["status"] == "CREATED"

        created = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={
                "title": "Unique Product",
                "description": "Valid product",
                "category_id": category_id,
                "slug": "unique-product",
                "images": _product_images(),
            },
        )
        assert created.status_code == 201
        assert created.json()["status"] == "CREATED"

        duplicate = client.post(
            "/api/v1/products",
            headers=seller_headers,
            json={
                "title": "Unique Product Again",
                "description": "Duplicate slug",
                "category_id": category_id,
                "slug": "unique-product",
                "images": _product_images(),
            },
        )
        assert duplicate.status_code == 409
