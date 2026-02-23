"""Models for parent-assigned tasks, habits, ideas, and parent settings."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ParentAssignedTask(Base):
    __tablename__ = "parent_assigned_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deadline: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # ISO date string

    # 1 | 2 | 3
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    # "study" | "practice" | "read" | "review" | "other"
    tag: Mapped[str] = mapped_column(String(32), nullable=False, default="study")

    # True = Bắt buộc (locked); False = Đề xuất
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # "TASK" | "IDEA_CONVERTED"
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="TASK")

    # ASSIGNED | SEEN | ACCEPTED | INPROGRESS | DONE | VERIFIED | ARCHIVED
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ASSIGNED", index=True)

    student_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reschedule_requested_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    reschedule_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ParentAssignedHabit(Base):
    __tablename__ = "parent_assigned_habits"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(256), nullable=False)

    # "daily" | "246" | "weekend" | "custom"
    frequency_type: Mapped[str] = mapped_column(String(32), nullable=False, default="daily")
    frequency_value: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    suggested_time: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # "HH:MM"

    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # "active" | "archived"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class HabitTick(Base):
    __tablename__ = "habit_ticks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    habit_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # "YYYY-MM-DD"
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ParentIdea(Base):
    __tablename__ = "parent_ideas"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # "task" | "habit"
    suggested_type: Mapped[str] = mapped_column(String(16), nullable=False, default="task")

    # "pending" | "accepted" | "later"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ParentSettings(Base):
    __tablename__ = "parent_settings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    parent_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)

    # "light" | "medium" | "strict"
    default_tone: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")

    default_remind_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)  # "HH:MM"

    require_verify_for_locked_tasks: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_student_reschedule: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # "Ba" | "Mẹ" | "Cô" | "Chú"
    salutation: Mapped[str] = mapped_column(String(16), nullable=False, default="Phụ huynh")

    # "light" | "medium" | "heavy"
    intervention_level: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ParentTaskItem(Base):
    """Checklist/subtask item belonging to a ParentAssignedTask."""
    __tablename__ = "parent_task_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    label: Mapped[str] = mapped_column(String(256), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    done_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    done_by: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # "student" | "parent"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TaskUpdate(Base):
    """Activity log entry on a ParentAssignedTask."""
    __tablename__ = "task_updates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # "student" | "parent"
    actor_role: Mapped[str] = mapped_column(String(16), nullable=False)

    # "quick_status" | "note" | "request_help" | "reschedule"
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="note")

    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
