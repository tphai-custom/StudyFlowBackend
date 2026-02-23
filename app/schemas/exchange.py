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
