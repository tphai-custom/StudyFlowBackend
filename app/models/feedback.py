from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True, server_default="")
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
