from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.dependencies import (
    get_current_user,
    require_role,
)
from app.core.repositories.user_repository import UserRepository
from app.api.v1.dependencies import get_user_repo

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

@router.post("/login", response_model=TokenResponseDTO)
async def login(
    data: LoginRequestDTO,
    repo: UserRepository = Depends(get_user_repo),
):
    user = await repo.get_by_email(data.email)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_session(str(user.id))

    return TokenResponseDTO(access_token=token)

@router.get("/me", response_model=MeResponseDTO)
async def me(
    user = Depends(get_current_user),
):
    return MeResponseDTO(user=user)

# Пример
@router.get("/admin")
async def admin_panel(
    user = Depends(require_role(UserRole.ADMIN)),
):
    return {"message": "welcome admin"}

@router.post("/logout")
async def logout(
    request: Request,
    user = Depends(get_current_user)
):
    delete_session(request.state.token)
    return {"message": "Logout"}