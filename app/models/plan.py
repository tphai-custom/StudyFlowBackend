from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlanRecord(Base):
    __tablename__ = "plan_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    sessions: Mapped[list] = mapped_column(JSONB, default=list)
    unscheduled_tasks: Mapped[list] = mapped_column(JSONB, default=list)
    suggestions: Mapped[list] = mapped_column(JSONB, default=list)
    generated_at: Mapped[str] = mapped_column(String, nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
