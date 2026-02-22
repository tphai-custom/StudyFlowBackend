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
