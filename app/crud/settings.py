from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import AppSettings
from app.schemas.settings import AppSettingsSchema

_DEFAULT_ID = "app-settings"


async def get_settings(db: AsyncSession) -> AppSettings:
    result = await db.execute(select(AppSettings).where(AppSettings.id == _DEFAULT_ID))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = AppSettings(
            id=_DEFAULT_ID,
            daily_limit_minutes=180,
            buffer_percent=0.15,
            break_preset={"focus": 45, "rest": 10, "label": "Deep work 45/10"},
            timezone="Asia/Ho_Chi_Minh",
            last_updated=datetime.utcnow(),
        )
        db.add(settings)
        await db.flush()
    return settings


async def save_settings(db: AsyncSession, payload: AppSettingsSchema) -> AppSettings:
    settings = await get_settings(db)
    settings.daily_limit_minutes = payload.daily_limit_minutes
    settings.buffer_percent = payload.buffer_percent
    settings.break_preset = payload.break_preset.model_dump()
    settings.timezone = payload.timezone
    settings.last_updated = datetime.utcnow()
    await db.flush()
    return settings
