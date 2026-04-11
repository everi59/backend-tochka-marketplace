from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.dependencies import (
    get_current_user,
    require_role,
)
from app.core.repositories.user_repository import UserRepository
from app.api.v1.dependencies import get_user_repo
from app.infrastructure.database.models import User

from app.utils.auth_service import (
    hash_password,
    verify_password,
)

from app.utils.auth_middleware import (
    create_session,
    delete_session,
)

from app.core.dto.user.user_dto import (
    RegisterRequestDTO,
    LoginRequestDTO,
    TokenResponseDTO,
    MeResponseDTO,
    UserDTO,
    UserRole,
)

router = APIRouter()

@router.post("/register", response_model=TokenResponseDTO)
async def register(
    data: RegisterRequestDTO,
    repo: UserRepository = Depends(get_user_repo),
):
    if await repo.get_by_field("nickname", data.nickname):
        raise HTTPException(400, "Nickname already exists")

    if await repo.get_by_field("email", data.nickname):
        raise HTTPException(400, "Nickname already exists")

    hashed = hash_password(data.password)

    user = await repo.create(
        User(
            email=data.email,
            hashed_password=hashed,
            nickname=data.nickname,
            first_name=data.first_name,
            second_name=data.second_name
        )
    )

    token = create_session(str(user.id))

    return TokenResponseDTO(access_token=token)

