from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.crud import settings as crud
from app.database import get_db
from app.models.user import User
from app.schemas.settings import AppSettingsSchema

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_model=AppSettingsSchema)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await crud.get_settings(db)


@router.put("/", response_model=AppSettingsSchema)
async def save_settings(
    payload: AppSettingsSchema,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await crud.save_settings(db, payload)
