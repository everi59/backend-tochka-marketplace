from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional

from app.core.base import ServiceError, utcnow
from app.core.services.base import BaseService


class AuthService(BaseService):
    def create_seller(self, data: dict[str, Any], prehashed: bool = False) -> dict[str, Any]:
        if any(s['email'] == data['email'] for s in self.store.sellers.values()):
            raise ServiceError('CONFLICT', 'Email already registered', 409)
        now = utcnow()
        seller = {
            'id': self.store.new_id(),
            'email': data['email'],
            'password_hash': data['password_hash'],
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'middle_name': data.get('middle_name'),
            'company_name': data['company_name'],
            'inn': data['inn'],
            'phone': data.get('phone'),
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        }
        self.store.sellers[seller['id']] = seller
        return seller

    def create_buyer(self, data: dict[str, Any]) -> dict[str, Any]:
        if any(b['email'] == data['email'] for b in self.store.buyers.values()):
            raise ServiceError('CONFLICT', 'Email already registered', 409)
        now = utcnow()
        buyer = {
            'id': self.store.new_id(),
            'email': data['email'],
            'password_hash': data['password_hash'],
            'first_name': data['first_name'],
            'last_name': data.get('last_name'),
            'phone': data.get('phone'),
            'date_of_birth': None,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        }
        self.store.buyers[buyer['id']] = buyer
        return buyer

    def issue_tokens(self, subject_id: str, role: str) -> dict[str, Any]:
        access = self.store.new_id()
        refresh = self.store.new_id()
        self.store.access_tokens[access] = {'sub': subject_id, 'role': role, 'exp': utcnow() + timedelta(hours=1)}
        self.store.refresh_tokens[refresh] = {'sub': subject_id, 'role': role, 'exp': utcnow() + timedelta(days=30)}
        return {
            'access_token': access,
            'refresh_token': refresh,
            'token_type': 'Bearer',
            'expires_in': 3600,
            'user_id': subject_id,
        }

    def refresh_pair(self, refresh_token: str) -> dict[str, Any]:
        payload = self.store.refresh_tokens.get(refresh_token)
        if not payload or payload['exp'] < utcnow():
            raise ServiceError('UNAUTHORIZED', 'Invalid refresh token', 401)
        del self.store.refresh_tokens[refresh_token]
        return self.issue_tokens(payload['sub'], payload['role'])

    def revoke_refresh(self, refresh_token: str) -> None:
        self.store.refresh_tokens.pop(refresh_token, None)

    def auth_subject(self, token: str, role: Optional[str] = None) -> dict[str, Any]:
        payload = self.store.access_tokens.get(token)
        if not payload or payload['exp'] < utcnow():
            raise ServiceError('UNAUTHORIZED', 'Invalid access token', 401)
        if role and payload['role'] != role:
            raise ServiceError('FORBIDDEN', 'Insufficient permissions', 403)
        if payload['role'] == 'seller':
            return self.store.sellers[payload['sub']]
        return self.store.buyers[payload['sub']]
