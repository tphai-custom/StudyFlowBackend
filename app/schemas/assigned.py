"""Pydantic schemas for parent-assigned tasks, habits, ideas, and parent settings."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ── Assigned Task ────────────────────────────────────────────────────────────

class AssignedTaskCreate(BaseModel):
    title: str
    subject: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[str] = None  # ISO date "YYYY-MM-DD"
    priority: int = 2  # 1-3
    tag: str = "study"  # study | practice | read | review | other
    locked: bool = False
    estimated_minutes: Optional[int] = None
    # B3: duration + scheduling style (set by parent when assigning)
    duration_mode: str = "estimate"  # exact | estimate
    duration_minutes_exact: Optional[int] = None
    duration_minutes_min: Optional[int] = None
    duration_minutes_max: Optional[int] = None
    scheduling_style: str = "balanced"  # front-load | balanced | deadline-loaded


class AssignedTaskUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[int] = None
    tag: Optional[str] = None
    locked: Optional[bool] = None
    status: Optional[str] = None  # ARCHIVED | VERIFIED + others
    estimated_minutes: Optional[int] = None
    duration_mode: Optional[str] = None
    duration_minutes_exact: Optional[int] = None
    duration_minutes_min: Optional[int] = None
    duration_minutes_max: Optional[int] = None
    scheduling_style: Optional[str] = None


class AssignedTaskSchema(BaseModel):
    id: str
    parent_id: str
    student_id: str
    title: str
    subject: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[str] = None
    priority: int
    tag: str
    locked: bool
    type: str
    status: str
    estimated_minutes: Optional[int] = None
    student_note: Optional[str] = None
    reschedule_requested_date: Optional[str] = None
    reschedule_reason: Optional[str] = None
    # B3: duration + style fields
    duration_mode: str = "estimate"
    duration_minutes_exact: Optional[int] = None
    duration_minutes_min: Optional[int] = None
    duration_minutes_max: Optional[int] = None
    scheduling_style: str = "balanced"
    converted_task_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConvertTaskResponse(BaseModel):
    """Response from POST /student/assigned-tasks/{id}/convert."""
    task_id: str               # newly created real Task id
    assignment_status: str     # always 'CONVERTED'
    already_converted: bool    # True if was already converted before this call


class StudentTaskEstimate(BaseModel):
    """Student sets estimated_minutes when accepting a parent task."""
    estimated_minutes: Optional[int] = None  # 15 | 30 | 45 | 60 | 90 | ...


class StudentTaskAction(BaseModel):
    """Student updates their own note or requests reschedule."""
    student_note: Optional[str] = None
    reschedule_requested_date: Optional[str] = None
    reschedule_reason: Optional[str] = None


# ── Assigned Habit ───────────────────────────────────────────────────────────

class AssignedHabitCreate(BaseModel):
    name: str
    frequency_type: str = "daily"  # daily | 246 | weekend | custom
    frequency_value: Optional[str] = None
    minutes: int = 15
    suggested_time: Optional[str] = None  # "HH:MM"
    locked: bool = False


class AssignedHabitUpdate(BaseModel):
    name: Optional[str] = None
    frequency_type: Optional[str] = None
    frequency_value: Optional[str] = None
    minutes: Optional[int] = None
    suggested_time: Optional[str] = None
    locked: Optional[bool] = None
    status: Optional[str] = None  # active | archived


class AssignedHabitSchema(BaseModel):
    id: str
    parent_id: str
    student_id: str
    name: str
    frequency_type: str
    frequency_value: Optional[str] = None
    minutes: int
    suggested_time: Optional[str] = None
    locked: bool
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class HabitDayStatus(BaseModel):
    date: str
    done: bool


class AssignedHabitWithStatus(AssignedHabitSchema):
    """Habit + today's tick status + streak (for student & parent views)."""
    ticked_today: bool = False
    ticked_at: Optional[datetime] = None
    streak: int = 0
    last_7_days: list[HabitDayStatus] = []


class HabitTickCreate(BaseModel):
    date: str  # "YYYY-MM-DD"
    note: Optional[str] = None


class HabitTickSchema(BaseModel):
    id: str
    habit_id: str
    student_id: str
    date: str
    completed: bool
    note: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Idea ─────────────────────────────────────────────────────────────────────

class IdeaCreate(BaseModel):
    content: str
    suggested_type: str = "task"  # task | habit


class IdeaSchema(BaseModel):
    id: str
    parent_id: str
    student_id: str
    content: str
    suggested_type: str
    status: str  # pending | accepted | later
    created_at: datetime

    model_config = {"from_attributes": True}


class IdeaAccept(BaseModel):
    convert_type: str = "task"  # task | habit


# ── Parent Settings ──────────────────────────────────────────────────────────

class ParentSettingsUpdate(BaseModel):
    default_tone: Optional[str] = None
    default_remind_time: Optional[str] = None
    require_verify_for_locked_tasks: Optional[bool] = None
    allow_student_reschedule: Optional[bool] = None
    salutation: Optional[str] = None
    intervention_level: Optional[str] = None


class ParentSettingsSchema(BaseModel):
    id: str
    parent_id: str
    default_tone: str
    default_remind_time: Optional[str] = None
    require_verify_for_locked_tasks: bool
    allow_student_reschedule: bool
    salutation: str
    intervention_level: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Parent Task Item (checklist) ─────────────────────────────────────────────

class TaskItemCreate(BaseModel):
    label: str
    subject: Optional[str] = None
    order_index: int = 0


class TaskItemUpdate(BaseModel):
    is_done: Optional[bool] = None
    label: Optional[str] = None
    subject: Optional[str] = None


class TaskItemSchema(BaseModel):
    id: str
    task_id: str
    label: str
    subject: Optional[str] = None
    order_index: int
    is_done: bool
    done_at: Optional[datetime] = None
    done_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Task Update (activity log) ────────────────────────────────────────────────

class TaskUpdateCreate(BaseModel):
    type: str = "note"  # quick_status | note | request_help | reschedule
    content: Optional[str] = None


class TaskUpdateSchema(BaseModel):
    id: str
    task_id: str
    actor_role: str
    type: str
    content: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
