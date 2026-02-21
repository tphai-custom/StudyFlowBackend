from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.crud import library as crud
from app.database import get_db
from app.models.user import User
from app.schemas.library import LibraryItemCreate, LibraryItemSchema

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/", response_model=list[LibraryItemSchema])
async def list_library(
    q: Optional[str] = None,
    subject: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if q or subject:
        return await crud.search_library(db, current_user.id, query=q, subject=subject)
    return await crud.list_library(db, current_user.id)


@router.post("/", response_model=list[LibraryItemSchema])
async def save_library_items(
    items: list[LibraryItemCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.save_library_items(db, items, current_user.id)
