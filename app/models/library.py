from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LibraryItem(Base):
    __tablename__ = "library_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    # NULL = system-shared content; set to user id for user-created items
    owner_user_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
