from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImportDraft(Base):
    __tablename__ = "import_drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # "template" or "program"
    draft_type: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    # list of DraftItem dicts (title, durationMin, difficulty, subject, successCriteria, orderIndex, notes)
    items: Mapped[list] = mapped_column(JSONB, default=list)
    # "draft" | "finalized"
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    owner_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
