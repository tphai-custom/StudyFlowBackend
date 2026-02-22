from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Allowed subjects (5 môn)
ALLOWED_SUBJECTS = ["toan", "ngu_van", "tieng_anh", "lich_su", "dia_li"]
# Subject display names
SUBJECT_LABELS = {
    "toan": "Toán",
    "ngu_van": "Ngữ văn",
    "tieng_anh": "Tiếng Anh",
    "lich_su": "Lịch sử",
    "dia_li": "Địa lí",
}
# Allowed resource types
ALLOWED_TYPES = ["lesson", "summary", "worksheet", "video", "book", "website"]


class LibraryItem(Base):
    __tablename__ = "library_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    subject: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # grade: 6..10. NULL = all grades / not grade-specific
    grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    level: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, default="lesson")
    difficulty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # NULL = system-shared content; set to user id for user-created items
    owner_user_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
