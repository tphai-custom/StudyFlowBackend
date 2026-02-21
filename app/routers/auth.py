from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.core.security import create_access_token
from app.crud import user as crud
from app.database import get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserLogin, UserPublic, UserRegister, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    # Admin accounts cannot be self-registered — they are seeded via admin script.
    if payload.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản quản trị do hệ thống cấp, không thể tự đăng ký.",
        )
    existing = await crud.get_user_by_username(db, payload.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username đã tồn tại")
    user = await crud.create_user(db, payload)
    token = create_access_token(user.id, {"role": user.role})
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await crud.authenticate_user(db, payload.username.lower(), payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai username hoặc mật khẩu",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")
    token = create_access_token(user.id, {"role": user.role})
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.get("/me", response_model=UserPublic)
async def me(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserPublic)
async def update_me(
    payload: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.update_user(db, current_user, payload)


@router.post("/rotate-link-code", response_model=UserPublic)
async def rotate_link_code(
    current_user: User = Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new link code for the student. Old code is immediately invalidated."""
    updated = await crud.rotate_link_code(db, current_user)
    await db.commit()
    await db.refresh(updated)
    return updated
