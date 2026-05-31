from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.store import NeoMarketStore


class BaseService:
    def __init__(self, store: NeoMarketStore) -> None:
        self.store = store
