from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import settings as crud
from app.database import get_db
from app.schemas.settings import AppSettingsSchema

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_model=AppSettingsSchema)
async def get_settings(db: AsyncSession = Depends(get_db)):
    return await crud.get_settings(db)


@router.put("/", response_model=AppSettingsSchema)
async def save_settings(payload: AppSettingsSchema, db: AsyncSession = Depends(get_db)):
    return await crud.save_settings(db, payload)
