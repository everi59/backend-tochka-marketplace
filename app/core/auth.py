from __future__ import annotations

import hashlib
from typing import Optional

from fastapi import Header

from app.core.store import NeoMarketStore, ServiceError


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash == "seed":
        return password == "sellerpass123"
    return hash_password(password) == password_hash


def extract_bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise ServiceError("UNAUTHORIZED", "Authorization header is required", 401)
    return authorization.split(" ", 1)[1]

