from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum
from typing import Optional

from app.infrastructure.database.models.user import UserRole


class RegisterRequestDTO(BaseModel):
    nickname: str
    email: str
    password: str
    first_name: Optional[str] = None
    second_name: Optional[str] = None


class LoginRequestDTO(BaseModel):
    email: str
    password: str


class TokenResponseDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserDTO(BaseModel):
    id: UUID
    nickname: str
    email: str
    first_name: Optional[str]
    second_name: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True


class MeResponseDTO(BaseModel):
    user: UserDTO