"""Router: admin user management and content management.

All endpoints require role=admin.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.crud import library as library_crud
from app.crud import user as user_crud
from app.database import get_db
from app.models.library import LibraryItem
from app.models.user import User
from app.schemas.library import LibraryItemCreate, LibraryItemSchema
from app.schemas.user import UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None


class ResetPasswordPayload(BaseModel):
    new_password: str


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    """List all users in the system."""
    return await user_crud.get_all_users(db)


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    user = await user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    return user


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    """Activate or deactivate a user account."""
    user = await user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    if payload.is_active is not None:
        user = await user_crud.set_active(db, user, payload.is_active)
    await db.commit()
    return user


@router.post("/users/{user_id}/reset-password", response_model=dict)
async def admin_reset_password(
    user_id: str,
    payload: ResetPasswordPayload,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    """Admin resets a user's password."""
    user = await user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    await user_crud.reset_password(db, user, payload.new_password)
    await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# System library content management
# ---------------------------------------------------------------------------

@router.get("/library", response_model=list[LibraryItemSchema])
async def admin_list_library(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    """List ALL library items (system-shared + every user's private items)."""
    result = await db.execute(select(LibraryItem).order_by(LibraryItem.subject, LibraryItem.title))
    return result.scalars().all()


@router.get("/library/system", response_model=list[LibraryItemSchema])
async def admin_list_system_library(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    """List only system-shared library items (owner_user_id IS NULL)."""
    result = await db.execute(
        select(LibraryItem)
        .where(LibraryItem.owner_user_id == None)  # noqa: E711
        .order_by(LibraryItem.subject, LibraryItem.title)
    )
    return result.scalars().all()


@router.post("/library", response_model=list[LibraryItemSchema], status_code=201)
async def admin_add_system_library(
    items: list[LibraryItemCreate],
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    """Add one or more system-shared library items (owner_user_id = NULL)."""
    saved = await library_crud.save_library_items(db, items, owner_user_id=None)
    await db.commit()
    return saved


@router.delete("/library/{item_id}", status_code=204)
async def admin_delete_library_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    """Delete any library item by ID (system or user-owned)."""
    result = await db.execute(delete(LibraryItem).where(LibraryItem.id == item_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    await db.commit()
