from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
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
    locked_by_parent: Mapped[bool] = mapped_column(default=False)
    created_by_role: Mapped[str] = mapped_column(String(16), default="student")
    owner_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Parent-task fields (added in migration k0l1m2n3o4p5) ─────────────────
    # source: 'student' | 'parent'
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="student")
    # locked = bắt buộc (parent sets true, planner prioritizes)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # repeat: 'none' | 'daily' | 'weekly'
    repeat: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    child_can_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    child_can_edit_core: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # ── Duration mode (added in migration l1m2n3o4p5q6) ─────────────────────
    # duration_mode: 'exact' | 'estimate'
    duration_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="estimate")
    # exact: single value in minutes
    duration_minutes_exact: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # estimate: min/max range in minutes
    duration_minutes_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_minutes_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Scheduling style (added in migration l1m2n3o4p5q6) ───────────────────
    # 'front-load' | 'balanced' | 'deadline-loaded'
    scheduling_style: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")

    # ── Target minutes (added in migration n2o3p4q5r6s7) ────────────────────
    # Computed: exact → exact_minutes; estimate → clamp(mid, min, max)
    # Planner uses this as a hard ceiling: sum(study_minutes) == target_minutes
    target_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
