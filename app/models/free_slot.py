from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FreeSlot(Base):
    __tablename__ = "free_slots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String, nullable=False)  # HH:mm
    end_time: Mapped[str] = mapped_column(String, nullable=False)  # HH:mm
    capacity_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, default="user")
    owner_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
