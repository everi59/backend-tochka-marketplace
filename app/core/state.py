from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NeoMarketState:
    sellers: dict[str, dict[str, Any]] = field(default_factory=dict)
    buyers: dict[str, dict[str, Any]] = field(default_factory=dict)
    categories: dict[str, dict[str, Any]] = field(default_factory=dict)
    products: dict[str, dict[str, Any]] = field(default_factory=dict)
    skus: dict[str, dict[str, Any]] = field(default_factory=dict)
    invoices: dict[str, dict[str, Any]] = field(default_factory=dict)
    images: dict[str, dict[str, Any]] = field(default_factory=dict)
    carts: dict[str, dict[str, Any]] = field(default_factory=dict)
    orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    notifications: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    payment_methods: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    addresses: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    favorites: dict[str, set[str]] = field(default_factory=dict)
    subscriptions: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    access_tokens: dict[str, dict[str, Any]] = field(default_factory=dict)
    refresh_tokens: dict[str, dict[str, Any]] = field(default_factory=dict)
    order_idempotency: dict[str, dict[str, Any]] = field(default_factory=dict)
    reserve_idempotency: dict[str, dict[str, Any]] = field(default_factory=dict)
    fulfill_idempotency: dict[str, dict[str, Any]] = field(default_factory=dict)
    event_idempotency: dict[str, dict[str, Any]] = field(default_factory=dict)
    moderation_idempotency: dict[str, dict[str, Any]] = field(default_factory=dict)
    b2b_events: list[dict[str, Any]] = field(default_factory=list)
    moderation_events: list[dict[str, Any]] = field(default_factory=list)
    moderation_cards: dict[str, dict[str, Any]] = field(default_factory=dict)
    blocking_reasons: list[dict[str, Any]] = field(default_factory=list)
    banners: list[dict[str, Any]] = field(default_factory=list)
    collections: list[dict[str, Any]] = field(default_factory=list)
    order_counter: int = 1
