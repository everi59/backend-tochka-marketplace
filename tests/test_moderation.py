from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

SERVICE_HEADERS = {"X-Service-Key": "svc"}
_slug_counter = 0


def _next_slug(prefix: str = "test-product") -> str:
    global _slug_counter
    _slug_counter += 1
    return f"{prefix}-{_slug_counter}"


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


def _seller_headers(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _get_category_id(client: TestClient) -> str:
    return client.get("/api/v1/categories").json()[0]["id"]


def _create_sku(client: TestClient, seller_h: dict, product_id: str, name: str = "SKU-1", price: int = 1000) -> dict:
    resp = client.post(
        "/api/v1/skus",
        headers=seller_h,
        json={
            "product_id": product_id,
            "name": name,
            "price": price,
            "article": f"ART-{name}",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _create_product(client: TestClient, seller_h: dict, category_id: str, title: str = "Test Product") -> dict:
    resp = client.post(
        "/api/v1/products",
        headers=seller_h,
        json={
            "title": title,
            "description": "Description for " + title,
            "category_id": category_id,
            "slug": _next_slug(title.lower().replace(" ", "-")),
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _emit_product_event(client: TestClient, product_id: str, seller_id: str, event_type: str) -> None:
    resp = client.post(
        "/api/v1/b2b/events",
        json={"event_type": event_type, "payload": {"product_id": product_id, "seller_id": seller_id}},
        headers=SERVICE_HEADERS,
    )
    assert resp.status_code == 202


def _get_next(client: TestClient, moderator_id: str = "mod-1", queue_priority: int | None = None) -> dict | None:
    payload = {}
    if queue_priority is not None:
        payload["queue_priority"] = queue_priority
    resp = client.post(
        "/api/v1/queue/claim",
        json=payload,
        headers={**SERVICE_HEADERS, "X-Moderator-Id": moderator_id},
    )
    if resp.status_code == 204:
        return None
    assert resp.status_code == 200
    return resp.json()


class TestMod1ProductCreatedEvent:
    def test_created_event(self):
        with TestClient(app) as client:
            seller = _create_seller(client, "mod1-seller@example.com", "1111111111")
            seller_h = _seller_headers(seller)
            category_id = _get_category_id(client)

            product = _create_product(client, seller_h, category_id, "Moderation Test")
            pid = product["id"]

            _emit_product_event(client, pid, seller["user_id"], "PRODUCT_CREATED")

            store = app.state.store
            card = store.moderation_cards.get(pid)
            assert card is not None
            assert card["status"] == "PENDING"
            assert card["json_before"] is None
            assert card["json_after"]["title"] == "Moderation Test"
            assert card["seller_id"] == seller["user_id"]

    def test_duplicate_created_returns_409(self):
        with TestClient(app) as client:
            seller = _create_seller(client, "mod1-dup@example.com", "1111111115")
            seller_h = _seller_headers(seller)
            category_id = _get_category_id(client)

            product = _create_product(client, seller_h, category_id, "Dup Test")
            pid = product["id"]

            _emit_product_event(client, pid, seller["user_id"], "PRODUCT_CREATED")

            resp = client.post(
                "/api/v1/b2b/events",
                json={"event_type": "PRODUCT_CREATED", "payload": {"product_id": pid, "seller_id": seller["user_id"]}},
                headers=SERVICE_HEADERS,
            )
            assert resp.status_code == 409

    def test_hard_blocked_product_ignores_created(self):
        with TestClient(app) as client:
            seller = _create_seller(client, "mod1-hb@example.com", "1111111112")
            seller_h = _seller_headers(seller)
            category_id = _get_category_id(client)

            product = _create_product(client, seller_h, category_id, "HB Product")
            pid = product["id"]

            _emit_product_event(client, pid, seller["user_id"], "PRODUCT_CREATED")
            _get_next(client, "mod-1")

            reasons = client.get("/api/v1/blocking-reasons", headers=SERVICE_HEADERS).json()
            hard_id = next(r["id"] for r in reasons if r["hard_block"])

            resp = client.post(
                f"/api/v1/tickets/{pid}/block",
                json={"blocking_reason_ids": [hard_id]},
                headers={**SERVICE_HEADERS, "X-Moderator-Id": "mod-1"},
            )
            assert resp.status_code == 200

            resp2 = client.post(
                "/api/v1/b2b/events",
                json={"event_type": "PRODUCT_CREATED", "payload": {"product_id": pid, "seller_id": seller["user_id"]}},
                headers=SERVICE_HEADERS,
            )
            assert resp2.status_code == 202

            store = app.state.store
            assert store.moderation_cards[pid]["status"] == "HARD_BLOCKED"


class TestMod1EditEvent:
    def test_edit_event(self):
        with TestClient(app) as client:
            seller = _create_seller(client, "mod1edit@example.com", "1111111113")
            seller_h = _seller_headers(seller)
            category_id = _get_category_id(client)

            product = _create_product(client, seller_h, category_id, "Edit Product")
            pid = product["id"]

            _emit_product_event(client, pid, seller["user_id"], "PRODUCT_CREATED")

            store = app.state.store
            card_before = store.moderation_cards.get(pid)
            assert card_before is not None
            assert card_before["json_before"] is None

            resp = client.put(
                f"/api/v1/products/{pid}",
                headers=seller_h,
                json={"title": "Edit Product 2", "description": "Updated", "category_id": category_id},
            )
            assert resp.status_code == 200

            _emit_product_event(client, pid, seller["user_id"], "PRODUCT_EDITED")

            card_after = store.moderation_cards.get(pid)
            assert card_after["json_before"]["title"] == "Edit Product"
            assert card_after["json_after"]["title"] == "Edit Product 2"


class TestMod2GetNext:
    def test_get_next_product(self):
        with TestClient(app) as client:
            seller = _create_seller(client, "mod2-seller@example.com", "2222222222")
            seller_h = _seller_headers(seller)
            category_id = _get_category_id(client)

            p1 = _create_product(client, seller_h, category_id, "Q1")
            p2 = _create_product(client, seller_h, category_id, "Q2")

            _emit_product_event(client, p1["id"], seller["user_id"], "PRODUCT_CREATED")
            _emit_product_event(client, p2["id"], seller["user_id"], "PRODUCT_CREATED")

            store = app.state.store
            assert len(store.moderation_cards) >= 2

            card = _get_next(client, "mod-1")
            assert card is not None
            assert card["status"] == "IN_REVIEW"
            assert "id" in card
            assert "kind" in card
            assert card["kind"] in ("CREATE", "EDIT")
            assert "created_at" in card

    def test_empty_queue(self):
        with TestClient(app) as client:
            card = _get_next(client, "mod-1")
            assert card is None

    def test_moderator_already_in_review_returns_409(self):
        with TestClient(app) as client:
            seller = _create_seller(client, "mod2-dup@example.com", "2222222223")
            seller_h = _seller_headers(seller)
            category_id = _get_category_id(client)

            p1 = _create_product(client, seller_h, category_id, "Q-Dup-1")
            _emit_product_event(client, p1["id"], seller["user_id"], "PRODUCT_CREATED")

            _get_next(client, "mod-1")

            p2 = _create_product(client, seller_h, category_id, "Q-Dup-2")
            _emit_product_event(client, p2["id"], seller["user_id"], "PRODUCT_CREATED")

            resp = client.post(
                "/api/v1/queue/claim",
                json={},
                headers={**SERVICE_HEADERS, "X-Moderator-Id": "mod-1"},
            )
            assert resp.status_code == 409


class TestMod3Approve:
    def test_approve_product(self):
        with TestClient(app) as client:
            seller = _create_seller(client, "mod3-seller@example.com", "3333333333")
            seller_h = _seller_headers(seller)
            category_id = _get_category_id(client)

            product = _create_product(client, seller_h, category_id, "Approve Product")
            pid = product["id"]
            _create_sku(client, seller_h, pid)

            _emit_product_event(client, pid, seller["user_id"], "PRODUCT_CREATED")
            card = _get_next(client, "mod-1")
            assert card is not None

            resp = client.post(
                f"/api/v1/tickets/{pid}/approve",
                json={"moderator_comment": "Looks good"},
                headers={**SERVICE_HEADERS, "X-Moderator-Id": "mod-1"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "APPROVED"
            assert body["kind"] == "CREATE"

            store = app.state.store
            assert store.moderation_cards[pid]["status"] == "APPROVED"


class TestMod4DeclineBlocked:
    def test_decline_blocked(self):
        with TestClient(app) as client:
            seller = _create_seller(client, "mod4-seller@example.com", "4444444444")
            seller_h = _seller_headers(seller)
            category_id = _get_category_id(client)

            product = _create_product(client, seller_h, category_id, "Decline Product")
            pid = product["id"]

            _emit_product_event(client, pid, seller["user_id"], "PRODUCT_CREATED")
            card = _get_next(client, "mod-1")
            assert card is not None

            reasons = client.get("/api/v1/blocking-reasons", headers=SERVICE_HEADERS).json()
            soft_id = next(r["id"] for r in reasons if not r["hard_block"])

            resp = client.post(
                f"/api/v1/tickets/{pid}/block",
                json={"blocking_reason_ids": [soft_id], "moderator_comment": "Needs work"},
                headers={**SERVICE_HEADERS, "X-Moderator-Id": "mod-1"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "BLOCKED"
            assert body["kind"] == "CREATE"

            store = app.state.store
            assert store.moderation_cards[pid]["status"] == "BLOCKED"
            assert store.moderation_cards[pid]["blocking_reason_id"] == soft_id


class TestMod5DeclineHardBlock:
    def test_decline_hard_block(self):
        with TestClient(app) as client:
            seller = _create_seller(client, "mod5-seller@example.com", "5555555555")
            seller_h = _seller_headers(seller)
            category_id = _get_category_id(client)

            product = _create_product(client, seller_h, category_id, "Hard Block Product")
            pid = product["id"]

            _emit_product_event(client, pid, seller["user_id"], "PRODUCT_CREATED")
            card = _get_next(client, "mod-1")
            assert card is not None

            reasons = client.get("/api/v1/blocking-reasons", headers=SERVICE_HEADERS).json()
            hard_id = next(r["id"] for r in reasons if r["hard_block"])

            resp = client.post(
                f"/api/v1/tickets/{pid}/block",
                json={"blocking_reason_ids": [hard_id]},
                headers={**SERVICE_HEADERS, "X-Moderator-Id": "mod-1"},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "HARD_BLOCKED"

            store = app.state.store
            assert store.moderation_cards[pid]["status"] == "HARD_BLOCKED"

    def test_hard_blocked_returns_403(self):
        with TestClient(app) as client:
            seller = _create_seller(client, "mod5-edit@example.com", "5555555556")
            seller_h = _seller_headers(seller)
            category_id = _get_category_id(client)

            product = _create_product(client, seller_h, category_id, "HB 403")
            pid = product["id"]

            _emit_product_event(client, pid, seller["user_id"], "PRODUCT_CREATED")
            _get_next(client, "mod-1")

            reasons = client.get("/api/v1/blocking-reasons", headers=SERVICE_HEADERS).json()
            hard_id = next(r["id"] for r in reasons if r["hard_block"])

            resp = client.post(
                f"/api/v1/tickets/{pid}/block",
                json={"blocking_reason_ids": [hard_id]},
                headers={**SERVICE_HEADERS, "X-Moderator-Id": "mod-1"},
            )
            assert resp.status_code == 200

            resp2 = client.post(
                f"/api/v1/tickets/{pid}/approve",
                json={},
                headers={**SERVICE_HEADERS, "X-Moderator-Id": "mod-1"},
            )
            assert resp2.status_code == 403


class TestMod6BlockingReasons:
    def test_blocking_reasons(self):
        with TestClient(app) as client:
            resp = client.get("/api/v1/blocking-reasons", headers=SERVICE_HEADERS)
            assert resp.status_code == 200
            reasons = resp.json()
            assert len(reasons) == 10
            hard = [r for r in reasons if r["hard_block"]]
            soft = [r for r in reasons if not r["hard_block"]]
            assert len(hard) == 3
            assert len(soft) == 7
            for r in reasons:
                assert "code" in r
                assert "is_active" in r
