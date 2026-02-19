from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default="app-settings")
    daily_limit_minutes: Mapped[int] = mapped_column(Integer, default=180)
    buffer_percent: Mapped[float] = mapped_column(Float, default=0.15)
    break_preset: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {"focus": 45, "rest": 10, "label": "Deep work 45/10"},
    )
    timezone: Mapped[str] = mapped_column(String, default="Asia/Ho_Chi_Minh")
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
