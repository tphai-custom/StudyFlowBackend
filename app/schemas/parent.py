"""Schemas for parent–student linking and suggestions."""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class LinkRequest(BaseModel):
    """Sent by a parent to link with a student using the student's link_code."""
    child_username: str
    link_code: str


class LinkSchema(BaseModel):
    id: str
    parent_id: str
    student_id: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LinkStatusUpdate(BaseModel):
    status: str  # active | rejected


class SuggestionCreate(BaseModel):
    type: str
    payload: dict[str, Any] = {}
    message: Optional[str] = None


class SuggestionSchema(BaseModel):
    id: str
    parent_id: str
    student_id: str
    type: str
    payload: dict[str, Any] = {}
    message: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SuggestionStatusUpdate(BaseModel):
    status: str  # accepted | rejected


class LinkedStudentSchema(BaseModel):
    """Enriched link record sent to the parent sidebar."""
    student_id: str
    username: str
    full_name: str
    linked_at: datetime


# ---- Weekly summary ----

class UpcomingDeadline(BaseModel):
    task_id: str
    title: str
    subject: str
    deadline: str
    days_left: int


class WeeklySummary(BaseModel):
    student_id: str
    week: str  # YYYY-WW
    total_minutes: int
    completion_rate: float  # 0-100
    upcoming_deadlines: List[UpcomingDeadline]
    alerts: List[str]
    total_sessions: int
    done_sessions: int
    free_slot_minutes: int
    planned_minutes: int


class DailySessionSummary(BaseModel):
    session_id: str
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    subject: Optional[str] = None
    planned_start: Optional[str] = None
    minutes: int
    status: str  # done | skip | pending


class DailyReport(BaseModel):
    student_id: str
    date: str  # YYYY-MM-DD
    total_planned_minutes: int
    total_done_minutes: int
    completion_rate: float  # 0-100
    sessions: List[DailySessionSummary]
    alerts: List[str]


# ---- Parent Settings Lock ----

LOCKABLE_FIELDS = ["daily_limit_minutes", "buffer_percent", "break_preset", "timezone"]


class SettingsLockUpdate(BaseModel):
    locked_fields: List[str]
    # Optional: specific values the parent wants to enforce.
    # Dict keys must be in locked_fields. If omitted, student's current value is preserved.
    locked_values: Optional[dict] = None


class SettingsLockSchema(BaseModel):
    student_id: str
    parent_id: str
    locked_fields: List[str]
    locked_values: Optional[dict] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---- Parent notes (P1 journal) ----

class NoteCreate(BaseModel):
    message: str
    tag: Optional[str] = "general"  # encourage | deadline | praise | update | general


class NoteSchema(BaseModel):
    id: str
    parent_id: str
    student_id: str
    message: str
    tag: str
    reaction: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NoteReaction(BaseModel):
    reaction: str  # 👍 | ok | khó quá | con đang làm


# ---- Nudge settings ----

class NudgeSettings(BaseModel):
    remind_hour: int = 20   # 0-23
    tone: str = "medium"    # light | medium | strict
