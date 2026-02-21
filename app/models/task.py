from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    deadline: Mapped[str] = mapped_column(String, nullable=False)  # ISO string
    timezone: Mapped[str] = mapped_column(String, default="Asia/Ho_Chi_Minh")
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_estimate_min: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_estimate_max: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_unit: Mapped[str] = mapped_column(String, default="minutes")
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    importance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_focus: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success_criteria: Mapped[list] = mapped_column(JSONB, default=list)
    milestones: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress_minutes: Mapped[int] = mapped_column(Integer, default=0)
    owner_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
