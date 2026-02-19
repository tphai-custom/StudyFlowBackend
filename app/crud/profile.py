from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import UserProfile
from app.schemas.profile import UserProfileUpdate

_DEFAULT_ID = "user-profile"


async def get_profile(db: AsyncSession) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.id == _DEFAULT_ID))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = UserProfile(
            id=_DEFAULT_ID,
            grade_level="Chưa thiết lập",
            goals=[],
            weak_subjects=[],
            strong_subjects=[],
            learning_pace="balanced",
            energy_preferences={"morning": "medium", "afternoon": "medium", "evening": "medium"},
            daily_limit_preference=180,
            favorite_break_preset="Pomodoro 50/10",
            timezone="Asia/Ho_Chi_Minh",
            updated_at=datetime.utcnow(),
        )
        db.add(profile)
        await db.flush()
    return profile


async def save_profile(db: AsyncSession, payload: UserProfileUpdate) -> UserProfile:
    profile = await get_profile(db)
    data = payload.model_dump(by_alias=False)
    for key, value in data.items():
        if key == "energy_preferences" and hasattr(value, "model_dump"):
            value = value.model_dump()
        setattr(profile, key, value)
    profile.updated_at = datetime.utcnow()
    await db.flush()
    return profile
