"""Models for parent–student exchange messages (Trao đổi)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExchangeMessage(Base):
    __tablename__ = "exchange_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # "parent" | "student"
    sender_role: Mapped[str] = mapped_column(String(16), nullable=False, default="parent")

    # "motivation" | "reminder" | "praise" | "suggestion" | "other"
    tag: Mapped[str] = mapped_column(String(32), nullable=False, default="other")

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # "unread" | "read" | "replied"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="unread")

    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Quick reply from student: "LIKE" | "DO_TODAY" | "RESCHEDULE" | "NEED_HELP"
    student_quick_reply: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    student_reply_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Set when student sends a quick-reply → status changes to "replied"
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
