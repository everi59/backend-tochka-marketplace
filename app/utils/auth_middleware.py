import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional

# in-memory sessions (dev only)
sessions: Dict[str, uuid] = {}  # token -> user_id


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user_id = None
        request.state.token = None

        token = self._extract_token(request)

        if token:
            user_id = sessions.get(token)
            if user_id:
                request.state.user_id = user_id
                request.state.token = token

        return await call_next(request)

    def _extract_token(self, request: Request) -> Optional[str]:
        auth = request.headers.get("authorization")

        if not auth:
            return None

        parts = auth.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]

def create_session(user_id: str) -> str:
    """
    Создаёт сессию и возвращает токен
    """
    token = str(uuid.uuid4())
    sessions[token] = user_id
    return token

def delete_session(token: str) -> None:
    """
    Удаляет сессию по токену
    """
    sessions.pop(token, None)
