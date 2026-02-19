from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default="user-profile")
    grade_level: Mapped[str] = mapped_column(String, default="Chưa thiết lập")
    goals: Mapped[list] = mapped_column(JSONB, default=list)
    weak_subjects: Mapped[list] = mapped_column(JSONB, default=list)
    strong_subjects: Mapped[list] = mapped_column(JSONB, default=list)
    learning_pace: Mapped[str] = mapped_column(String, default="balanced")
    energy_preferences: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {"morning": "medium", "afternoon": "medium", "evening": "medium"},
    )
    daily_limit_preference: Mapped[int] = mapped_column(Integer, default=180)
    favorite_break_preset: Mapped[str] = mapped_column(String, default="Pomodoro 50/10")
    timezone: Mapped[str] = mapped_column(String, default="Asia/Ho_Chi_Minh")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
