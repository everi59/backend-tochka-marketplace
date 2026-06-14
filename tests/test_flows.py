from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app.main import app


SERVICE_HEADERS = {"X-Service-Key": "svc"}
_slug_counter = 0


def _next_slug(prefix: str = "test-product") -> str:
    global _slug_counter
    _slug_counter += 1
    return f"{prefix}-{_slug_counter}"


def _product_images() -> list[dict[str, object]]:
    return [{"url": "https://example.com/product.jpg", "ordering": 0}]


def _sku_payload(product_id: str, name: str = "SKU", price: int = 1000, article: str = "ART-1") -> dict[str, object]:
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


def _seller_id(tokens: dict[str, str]) -> str:
    return tokens["user_id"]


def _seller_headers(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _get_category_id(client: TestClient) -> str:
    return client.get("/api/v1/categories").json()[0]["id"]


def _create_product(client: TestClient, seller_h: dict, category_id: str, title: str = "Test Product") -> dict:
    resp = client.post(
        "/api/v1/products",
        headers=seller_h,
        json={
            "title": title,
            "description": "Description for " + title,
            "category_id": category_id,
            "slug": _next_slug(title.lower().replace(" ", "-")),
            "images": _product_images(),
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _create_sku(client: TestClient, seller_h: dict, product_id: str, name: str = "SKU-1", price: int = 1000) -> dict:
    resp = client.post(
        "/api/v1/skus",
        headers=seller_h,
        json=_sku_payload(product_id, name, price, f"ART-{name}"),
    )
    assert resp.status_code == 201
    return resp.json()


def _moderate_product(client: TestClient, product_id: str) -> None:
    resp = client.post(
        "/api/v1/moderation/events",
        headers=SERVICE_HEADERS,
        json={
            "idempotency_key": f"mod-{product_id}",
            "product_id": product_id,
            "event_type": "MODERATED",
            "occurred_at": "2026-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 204


def _seed_product_with_sku(client: TestClient, seller_h: dict, category_id: str) -> tuple[dict, dict]:
    product = _create_product(client, seller_h, category_id)
    sku = _create_sku(client, seller_h, product["id"])
    return product, sku


# ============================================================
# B2B-1: Создание товара
# ============================================================
def test_b2b_1_create_product() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b1-seller@example.com", "1111111111")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)

        resp = client.post(
            "/api/v1/products",
            headers=seller_h,
            json={
                "title": "iPhone 15 Pro Max",
                "description": "Флагманский смартфон Apple",
                "category_id": category_id,
                "images": _product_images(),
                "characteristics": [
                    {"name": "Бренд", "value": "Apple"},
                ],
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "iPhone 15 Pro Max"
        assert body["status"] == "CREATED"
        assert body["deleted"] is False
        assert body["seller_id"] == _seller_id(seller)
        assert body["category_id"] == category_id
        assert len(body["images"]) == 1
        assert body["skus"] == []

        no_images = client.post(
            "/api/v1/products",
            headers=seller_h,
            json={
                "title": "No images",
                "description": "Optional images",
                "category_id": category_id,
            },
        )
        assert no_images.status_code == 201

        bad_category = client.post(
            "/api/v1/products",
            headers=seller_h,
            json={
                "title": "Bad",
                "description": "Bad category",
                "category_id": "00000000-0000-0000-0000-000000000000",
                "images": _product_images(),
            },
        )
        assert bad_category.status_code == 404


# ============================================================
# B2B-2: Создание SKU
# ============================================================
def test_b2b_2_create_sku() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b2-seller@example.com", "2222222222")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        product = _create_product(client, seller_h, category_id)

        assert product["status"] == "CREATED"

        sku = _create_sku(client, seller_h, product["id"], "256GB Black", 12999000)
        assert sku["product_id"] == product["id"]
        assert sku["price"] == 12999000

        updated = client.get(f"/api/v1/products/{product['id']}", headers=seller_h).json()
        assert updated["status"] == "ON_MODERATION"
        assert len(updated["skus"]) == 1

        mod_events = client.app.state.store.moderation_events
        last_mod = [e for e in mod_events if e.get("product_id") == product["id"]]
        assert any(e["event_type"] == "PRODUCT_CREATED" for e in last_mod)


# ============================================================
# B2B-3: Редактирование товара/SKU
# ============================================================
def test_b2b_3_edit_product_and_sku() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b3-seller@example.com", "3333333333")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        product, sku = _seed_product_with_sku(client, seller_h, category_id)
        _moderate_product(client, product["id"])

        resp = client.patch(
            f"/api/v1/products/{product['id']}",
            headers=seller_h,
            json={"title": "Updated Title"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"
        assert resp.json()["status"] == "ON_MODERATION"

        other = _create_seller(client, "b2b3-other@example.com", "3333333334")
        other_h = _seller_headers(other)
        forbidden = client.patch(
            f"/api/v1/products/{product['id']}",
            headers=other_h,
            json={"title": "Hacked"},
        )
        assert forbidden.status_code == 403

        product2, sku2 = _seed_product_with_sku(client, seller_h, category_id)
        _moderate_product(client, product2["id"])
        app.state.store.products[product2["id"]]["status"] = "HARD_BLOCKED"
        blocked_edit = client.patch(
            f"/api/v1/products/{product2['id']}",
            headers=seller_h,
            json={"title": "Try"},
        )
        assert blocked_edit.status_code == 403

        sku_resp = client.patch(
            f"/api/v1/skus/{sku['id']}",
            headers=seller_h,
            json={"name": "Updated SKU"},
        )
        assert sku_resp.status_code == 200
        assert sku_resp.json()["name"] == "Updated SKU"


# ============================================================
# B2B-4: Удаление товара
# ============================================================
def test_b2b_4_delete_product() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b4-seller@example.com", "4444444444")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        product = _create_product(client, seller_h, category_id)

        resp = client.delete(f"/api/v1/products/{product['id']}", headers=seller_h)
        assert resp.status_code == 204
        assert app.state.store.products[product["id"]]["deleted"] is True

        mod_events = app.state.store.moderation_events
        assert any(
            e.get("product_id") == product["id"] and e["event_type"] == "PRODUCT_DELETED"
            for e in mod_events
        )
        b2b_events = app.state.store.b2b_events
        assert any(
            e["event_type"] == "PRODUCT_DELETED" and e["payload"]["product_id"] == product["id"]
            for e in b2b_events
        )

        repeat = client.delete(f"/api/v1/products/{product['id']}", headers=seller_h)
        assert repeat.status_code == 400

        product2 = _create_product(client, seller_h, category_id, "Delete Me")
        other = _create_seller(client, "b2b4-other@example.com", "4444444445")
        other_h = _seller_headers(other)
        forbidden = client.delete(f"/api/v1/products/{product2['id']}", headers=other_h)
        assert forbidden.status_code == 403

        product3 = _create_product(client, seller_h, category_id, "Hard Blocked")
        app.state.store.products[product3["id"]]["status"] = "HARD_BLOCKED"
        hard_blocked = client.delete(f"/api/v1/products/{product3['id']}", headers=seller_h)
        assert hard_blocked.status_code == 403


# ============================================================
# B2B-5: Просмотр статуса и блокировки
# ============================================================
def test_b2b_5_view_product_status() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b5-seller@example.com", "5555555555")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        product, sku = _seed_product_with_sku(client, seller_h, category_id)
        _moderate_product(client, product["id"])

        resp = client.get(f"/api/v1/products/{product['id']}", headers=seller_h)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "MODERATED"
        assert body["blocking_reason"] is None
        assert body["field_reports"] == []
        assert len(body["skus"]) == 1

        app.state.store.products[product["id"]]["status"] = "BLOCKED"
        app.state.store.products[product["id"]]["blocking_reason"] = {
            "id": "reason-1",
            "title": "Нарушение",
            "comment": "Описание не соответствует",
        }
        app.state.store.products[product["id"]]["field_reports"] = [
            {"field_name": "description", "sku_id": None, "comment": "Скопировано"}
        ]
        blocked_resp = client.get(f"/api/v1/products/{product['id']}", headers=seller_h)
        assert blocked_resp.status_code == 200
        blocked_body = blocked_resp.json()
        assert blocked_body["status"] == "BLOCKED"
        assert blocked_body["blocking_reason"]["title"] == "Нарушение"
        assert len(blocked_body["field_reports"]) == 1

        other = _create_seller(client, "b2b5-other@example.com", "5555555556")
        other_h = _seller_headers(other)
        not_found = client.get(f"/api/v1/products/{product['id']}", headers=other_h)
        assert not_found.status_code == 403

        svc_resp = client.get(f"/api/v1/products/{product['id']}", headers=SERVICE_HEADERS)
        assert svc_resp.status_code == 200


# ============================================================
# B2B-6: Создание и приёмка накладной
# ============================================================
def test_b2b_6_invoice_lifecycle() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b6-seller@example.com", "6666666666")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        product, sku = _seed_product_with_sku(client, seller_h, category_id)
        _moderate_product(client, product["id"])

        empty = client.post("/api/v1/invoices", headers=seller_h, json={"items": []})
        assert empty.status_code == 400

        resp = client.post(
            "/api/v1/invoices",
            headers=seller_h,
            json={"items": [{"sku_id": sku["id"], "quantity": 10}]},
        )
        assert resp.status_code == 201
        invoice = resp.json()
        assert invoice["status"] == "CREATED"
        assert len(invoice["items"]) == 1

        other = _create_seller(client, "b2b6-other@example.com", "6666666667")
        other_h = _seller_headers(other)
        forbidden = client.post(
            "/api/v1/invoices",
            headers=other_h,
            json={"items": [{"sku_id": sku["id"], "quantity": 5}]},
        )
        assert forbidden.status_code == 403

        accept = client.post(
            f"/api/v1/invoices/{invoice['id']}/accept",
            headers=seller_h,
            json={"items": [{"sku_id": sku["id"], "accepted_quantity": 7}]},
        )
        assert accept.status_code == 200
        assert accept.json()["status"] == "PARTIALLY_ACCEPTED"

        updated_sku = client.get(f"/api/v1/skus/{sku['id']}", headers=seller_h).json()
        assert updated_sku["stock_quantity"] == sku.get("stock_quantity", 0) + 7


# ============================================================
# B2B-7: Endpoints для B2C каталога
# ============================================================
def test_b2b_7_b2c_catalog_endpoints() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b7-seller@example.com", "7777777777")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        product, sku = _seed_product_with_sku(client, seller_h, category_id)
        _moderate_product(client, product["id"])
        app.state.store.skus[sku["id"]]["stock_quantity"] = 5

        resp = client.get("/api/v1/public/products", headers=SERVICE_HEADERS)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(p["id"] == product["id"] for p in items)
        pub_sku = next(p for p in items if p["id"] == product["id"])
        assert "cost_price" not in str(pub_sku)

        batch = client.post(
            "/api/v1/public/products/batch",
            headers=SERVICE_HEADERS,
            json={"ids": [product["id"]]},
        )
        assert batch.status_code == 200

        detail = client.get(f"/api/v1/public/products/{product['id']}", headers=SERVICE_HEADERS)
        assert detail.status_code == 200

        app.state.store.products[product["id"]]["status"] = "ON_MODERATION"
        hidden = client.get("/api/v1/public/products", headers=SERVICE_HEADERS)
        hidden_ids = [p["id"] for p in hidden.json()["items"]]
        assert product["id"] not in hidden_ids

        no_key = client.get("/api/v1/public/products")
        assert no_key.status_code == 401


# ============================================================
# B2B-8: Reserve / Unreserve
# ============================================================
def test_b2b_8_reserve_unreserve() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b8-seller@example.com", "8888888888")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        product, sku = _seed_product_with_sku(client, seller_h, category_id)
        _moderate_product(client, product["id"])
        app.state.store.skus[sku["id"]]["stock_quantity"] = 10

        resp = client.post(
            "/api/v1/reserve",
            headers=SERVICE_HEADERS,
            json={
                "idempotency_key": "res-1",
                "order_id": "ord-1",
                "items": [{"sku_id": sku["id"], "quantity": 3}],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "RESERVED"

        s = app.state.store.skus[sku["id"]]
        assert s["reserved_quantity"] == 3

        idempotent = client.post(
            "/api/v1/reserve",
            headers=SERVICE_HEADERS,
            json={
                "idempotency_key": "res-1",
                "order_id": "ord-1",
                "items": [{"sku_id": sku["id"], "quantity": 3}],
            },
        )
        assert idempotent.status_code == 200

        over = client.post(
            "/api/v1/reserve",
            headers=SERVICE_HEADERS,
            json={
                "idempotency_key": "res-2",
                "order_id": "ord-2",
                "items": [{"sku_id": sku["id"], "quantity": 100}],
            },
        )
        assert over.status_code == 409

        unreserve = client.post(
            "/api/v1/unreserve",
            headers=SERVICE_HEADERS,
            json={
                "order_id": "ord-1",
                "items": [{"sku_id": sku["id"], "quantity": 3}],
            },
        )
        assert unreserve.status_code == 200
        assert app.state.store.skus[sku["id"]]["reserved_quantity"] == 0


# ============================================================
# B2B-9: Обработка событий модерации
# ============================================================
def test_b2b_9_moderation_events() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b9-seller@example.com", "9999999999")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        product, sku = _seed_product_with_sku(client, seller_h, category_id)

        resp = client.post(
            "/api/v1/events/moderation",
            headers=SERVICE_HEADERS,
            json={
                "idempotency_key": "mod-ok-1",
                "product_id": product["id"],
                "status": "MODERATED",
                "occurred_at": "2026-01-01T00:00:00Z",
            },
        )
        assert resp.status_code == 200
        assert app.state.store.products[product["id"]]["status"] == "MODERATED"

        resp2 = client.post(
            "/api/v1/events/moderation",
            headers=SERVICE_HEADERS,
            json={
                "idempotency_key": "mod-ok-1",
                "product_id": product["id"],
                "status": "MODERATED",
                "occurred_at": "2026-01-01T00:00:00Z",
            },
        )
        assert resp2.status_code == 200

        resp3 = client.post(
            "/api/v1/events/moderation",
            headers=SERVICE_HEADERS,
            json={
                "idempotency_key": "mod-block-1",
                "product_id": product["id"],
                "status": "BLOCKED",
                "hard_block": False,
                "blocking_reason": {"id": "r1", "title": "Причина", "comment": "Комментарий"},
                "field_reports": [{"field_name": "description", "sku_id": None, "comment": "Текст"}],
                "occurred_at": "2026-01-01T00:00:00Z",
            },
        )
        assert resp3.status_code == 200
        assert app.state.store.products[product["id"]]["status"] == "BLOCKED"
        assert app.state.store.products[product["id"]]["blocking_reason"]["title"] == "Причина"


# ============================================================
# B2B-10: Fulfill (списание резерва при доставке)
# ============================================================
def test_b2b_10_fulfill() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b10-seller@example.com", "1010101010")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        product, sku = _seed_product_with_sku(client, seller_h, category_id)
        _moderate_product(client, product["id"])
        app.state.store.skus[sku["id"]]["stock_quantity"] = 10

        client.post(
            "/api/v1/reserve",
            headers=SERVICE_HEADERS,
            json={
                "idempotency_key": "res-fulfill",
                "order_id": "ord-fulfill",
                "items": [{"sku_id": sku["id"], "quantity": 5}],
            },
        )
        s = app.state.store.skus[sku["id"]]
        assert s["reserved_quantity"] == 5
        assert s["stock_quantity"] == 10

        resp = client.post(
            "/api/v1/fulfill",
            headers=SERVICE_HEADERS,
            json={
                "order_id": "ord-fulfill",
                "items": [{"sku_id": sku["id"], "quantity": 5}],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "FULFILLED"

        s2 = app.state.store.skus[sku["id"]]
        assert s2["reserved_quantity"] == 0
        assert s2["stock_quantity"] == 5

        idempotent = client.post(
            "/api/v1/fulfill",
            headers=SERVICE_HEADERS,
            json={
                "order_id": "ord-fulfill",
                "items": [{"sku_id": sku["id"], "quantity": 5}],
            },
        )
        assert idempotent.status_code == 200

        over = client.post(
            "/api/v1/fulfill",
            headers=SERVICE_HEADERS,
            json={
                "order_id": "ord-over",
                "items": [{"sku_id": sku["id"], "quantity": 999}],
            },
        )
        assert over.status_code == 409


# ============================================================
# B2B-11: Список товаров продавца
# ============================================================
def test_b2b_11_list_seller_products() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b11-seller@example.com", "1111111112")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        p1 = _create_product(client, seller_h, category_id, "Product A Unique")
        p2 = _create_product(client, seller_h, category_id, "Product B Unique")

        resp = client.get("/api/v1/products", headers=seller_h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] >= 2
        item_ids = {item["id"] for item in data["items"]}
        assert p1["id"] in item_ids
        assert p2["id"] in item_ids

        resp2 = client.get("/api/v1/products", headers=seller_h, params={"status": "CREATED"})
        assert resp2.status_code == 200
        for item in resp2.json()["items"]:
            assert item["status"] == "CREATED"

        other = _create_seller(client, "b2b11-other@example.com", "1111111113")
        other_h = _seller_headers(other)
        other_resp = client.get("/api/v1/products", headers=other_h)
        assert other_resp.status_code == 200
        other_ids = {item["id"] for item in other_resp.json()["items"]}
        assert p1["id"] not in other_ids
        assert p2["id"] not in other_ids


# ============================================================
# B2B-12: Удаление SKU
# ============================================================
def test_b2b_12_delete_sku() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b12-seller@example.com", "1212121212")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        product, sku = _seed_product_with_sku(client, seller_h, category_id)

        app.state.store.products[product["id"]]["status"] = "HARD_BLOCKED"
        blocked_del = client.delete(f"/api/v1/skus/{sku['id']}", headers=seller_h)
        assert blocked_del.status_code == 403

        app.state.store.products[product["id"]]["status"] = "ON_MODERATION"
        app.state.store.skus[sku["id"]]["reserved_quantity"] = 1
        reserved_del = client.delete(f"/api/v1/skus/{sku['id']}", headers=seller_h)
        assert reserved_del.status_code == 409

        app.state.store.skus[sku["id"]]["reserved_quantity"] = 0
        deleted = client.delete(f"/api/v1/skus/{sku['id']}", headers=seller_h)
        assert deleted.status_code == 204
        assert app.state.store.products[product["id"]]["status"] == "CREATED"
        assert sku["id"] not in app.state.store.products[product["id"]]["skus"]

        other = _create_seller(client, "b2b12-other@example.com", "1212121213")
        other_h = _seller_headers(other)
        product2, sku2 = _seed_product_with_sku(client, seller_h, category_id)
        forbidden = client.delete(f"/api/v1/skus/{sku2['id']}", headers=other_h)
        assert forbidden.status_code == 403


# ============================================================
# B2B-13: Загрузка и удаление изображения
# ============================================================
def test_b2b_13_image_upload_and_delete() -> None:
    with TestClient(app) as client:
        seller = _create_seller(client, "b2b13-seller@example.com", "1313131313")
        seller_h = _seller_headers(seller)
        category_id = _get_category_id(client)
        product = _create_product(client, seller_h, category_id)

        resp = client.post(
            "/api/v1/products",
            headers=seller_h,
            json={
                "title": "Image Test",
                "description": "Test",
                "category_id": category_id,
                "images": [{"url": "https://example.com/img.jpg", "ordering": 0}],
            },
        )
        assert resp.status_code == 201

        img_resp = client.post(
            f"/api/v1/products/{product['id']}/images",
            headers=seller_h,
            json={"url": "https://example.com/new.jpg", "ordering": 1},
        )
        assert img_resp.status_code == 201
        img = img_resp.json()
        assert img["url"] == "https://example.com/new.jpg"

        other = _create_seller(client, "b2b13-other@example.com", "1313131314")
        other_h = _seller_headers(other)
        forbidden = client.post(
            f"/api/v1/products/{product['id']}/images",
            headers=other_h,
            json={"url": "https://example.com/hack.jpg", "ordering": 0},
        )
        assert forbidden.status_code == 403

        del_resp = client.delete(
            f"/api/v1/products/images/{img['id']}",
            headers=seller_h,
        )
        assert del_resp.status_code == 204


# ============================================================
# B2C-1: Каталог с фильтрами
# ============================================================
def test_b2c_1_catalog_with_filters() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/v1/catalog/products")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total_count" in data
        assert "limit" in data
        assert "offset" in data

        resp2 = client.get("/api/v1/catalog/products", params={"sort": "price_asc"})
        assert resp2.status_code == 200

        resp3 = client.get("/api/v1/catalog/products", params={"sort": "zzz"})
        assert resp3.status_code == 400

        if data["items"]:
            cat_id = data["items"][0]["category_id"]
            resp4 = client.get("/api/v1/catalog/products", params={"category_id": cat_id})
            assert resp4.status_code == 200

        facets_resp = client.get("/api/v1/catalog/facets", params={"category_id": "nonexistent"})
        assert facets_resp.status_code == 404

        if data["items"]:
            cat_id = data["items"][0]["category_id"]
            facets_ok = client.get("/api/v1/catalog/facets", params={"category_id": cat_id})
            assert facets_ok.status_code == 200
            assert "facets" in facets_ok.json()


# ============================================================
# B2C-2: Текстовый поиск
# ============================================================
def test_b2c_2_search() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/v1/catalog/products", params={"q": "iPhone"})
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any("iPhone" in item.get("title", "") for item in items)

        resp2 = client.get("/api/v1/catalog/products", params={"q": "xyzzy_no_match"})
        assert resp2.status_code == 200
        assert resp2.json()["total_count"] == 0


# ============================================================
# B2C-3: Карточка товара
# ============================================================
def test_b2c_3_product_card() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/v1/catalog/products")
        if not resp.json()["items"]:
            return
        product_id = resp.json()["items"][0]["id"]

        detail = client.get(f"/api/v1/catalog/products/{product_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["id"] == product_id
        assert "title" in body
        assert "images" in body
        assert "skus" in body
        assert "description" in body

        for sku in body["skus"]:
            assert "cost_price" not in sku
            assert "reserved_quantity" not in sku


# ============================================================
# B2C-4: Похожие товары
# ============================================================
def test_b2c_4_similar_products() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/v1/catalog/products")
        if not resp.json()["items"]:
            return
        product = resp.json()["items"][0]

        similar = client.get(
            f"/api/v1/catalog/products/{product['id']}/similar",
            params={"limit": 8},
        )
        assert similar.status_code == 200
        for item in similar.json():
            assert "id" in item
            assert item["id"] != product["id"]


# ============================================================
# B2C-5: Категории и навигация
# ============================================================
def test_b2c_5_categories() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/v1/catalog/categories")
        assert resp.status_code == 200
        cats = resp.json()
        assert len(cats) > 0
        for cat in cats:
            assert "id" in cat
            assert "name" in cat

        tree = client.get("/api/v1/catalog/categories/tree")
        assert tree.status_code == 200

        breadcrumbs = client.get(f"/api/v1/categories/{cats[0]['id']}/breadcrumbs")
        assert breadcrumbs.status_code == 200
        data = breadcrumbs.json()
        assert len(data) >= 1
        assert data[-1]["id"] == cats[0]["id"]
