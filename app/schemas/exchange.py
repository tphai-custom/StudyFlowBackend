"""Pydantic schemas for exchange messages (Trao đổi)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ExchangeMessageCreate(BaseModel):
    content: str
    tag: str = "other"  # motivation | reminder | praise | suggestion | other


class ExchangeMessageSchema(BaseModel):
    id: str
    parent_id: str
    student_id: str
    sender_role: str
    tag: str
    content: str
    status: str  # unread | read | replied
    read_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    student_quick_reply: Optional[str] = None
    student_reply_text: Optional[str] = None
    pinned: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BadgeCountSchema(BaseModel):
    unread_count: int
    needs_action_count: int = 0


class QuickReplyCreate(BaseModel):
    quick_reply: str  # LIKE | DO_TODAY | RESCHEDULE | NEED_HELP
    reply_text: Optional[str] = None


class MessageActionCreateTask(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None


class MessageActionAddChecklist(BaseModel):
    task_id: str
    item: str


class MessageActionCreateSession(BaseModel):
    minutes: int = 25  # 25 or 45


class UnreadCountSchema(BaseModel):
    unread_count: int


# ── Dashboard summary schemas ─────────────────────────────────────────────────

class TodayHabitSummary(BaseModel):
    total: int
    done: int
    undone_ids: list[str]


class ExchangeSummary(BaseModel):
    """GET /student/dashboard/exchange-summary"""
    unread_parent_messages: int
    open_parent_tasks: int
    today_parent_habits: TodayHabitSummary

    @property
    def total_badge(self) -> int:
        """Sum of all pending items for sidebar badge."""
        return (
            self.unread_parent_messages
            + self.open_parent_tasks
            + max(0, self.today_parent_habits.total - self.today_parent_habits.done)
        )


class ExchangeBadgeSummary(BaseModel):
    """Short version for sidebar badge — GET /exchange/badge-summary"""
    unread_messages: int
    need_reply_messages: int = 0
    pending_parent_tasks: int = 0  # ASSIGNED|SEEN tasks not yet acted on
    pending_parent_habits_today: int = 0
    # legacy aliases kept for backwards-compat
    pending_tasks: int = 0
    pending_habits: int = 0
    total_badge: int


class SessionProgressBlock(BaseModel):
    done_sessions: int
    planned_sessions: int
    done_minutes: int
    planned_minutes: int


class ProgressSummary(BaseModel):
    """GET /student/dashboard/progress-summary"""
    today: SessionProgressBlock
    week: SessionProgressBlock


class BannerItem(BaseModel):
    key: str       # unique key for dedup
    level: str     # "info" | "warning" | "error"
    message: str
    href: Optional[str] = None

