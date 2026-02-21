from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    cadence: Mapped[str] = mapped_column(String, nullable=False)  # "daily"|"weekly"
    weekday: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    preset: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    preferred_start: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    energy_window: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    owner_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
