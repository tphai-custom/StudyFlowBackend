from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.crud import profile as crud
from app.database import get_db
from app.models.user import User
from app.schemas.profile import UserProfileSchema, UserProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/", response_model=UserProfileSchema)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await crud.get_profile(db)


@router.put("/", response_model=UserProfileSchema)
async def save_profile(
    payload: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await crud.save_profile(db, payload)
