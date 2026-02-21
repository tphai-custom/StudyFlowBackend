from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # pending | active | rejected
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ParentSuggestion(Base):
    __tablename__ = "parent_suggestions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_id: Mapped[str] = mapped_column(String, nullable=False)
    student_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # pending | accepted | rejected
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
