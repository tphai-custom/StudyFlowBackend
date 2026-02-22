from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PlanOverride(Base):
    __tablename__ = "plan_overrides"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    plan_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    date_start: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    date_end: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # List of modified session objects
    payload: Mapped[list] = mapped_column(JSONB, default=list)
    edited_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
