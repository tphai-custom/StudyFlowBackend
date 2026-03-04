from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, Field


class TaskMilestoneSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    minutes_estimate: int = Field(alias="minutesEstimate", ge=5)

    model_config = {"populate_by_name": True}


class TaskBase(BaseModel):
    subject: str
    title: str
    deadline: str  # ISO string
    timezone: str = "Asia/Ho_Chi_Minh"
    difficulty: Literal[1, 2, 3, 4, 5]
    duration_estimate_min: int = Field(alias="durationEstimateMin", ge=1)
    duration_estimate_max: int = Field(alias="durationEstimateMax", ge=1)
    duration_unit: Literal["minutes", "hours"] = Field(alias="durationUnit", default="minutes")
    estimated_minutes: int = Field(alias="estimatedMinutes", ge=1)
    importance: Optional[Literal[1, 2, 3]] = None
    content_focus: Optional[str] = Field(alias="contentFocus", default=None)
    success_criteria: list[str] = Field(alias="successCriteria", default_factory=list)
    milestones: Optional[list[TaskMilestoneSchema]] = None
    notes: Optional[str] = None
    # P1: duration mode
    duration_mode: Literal["exact", "estimate"] = Field(alias="durationMode", default="estimate")
    duration_minutes_exact: Optional[int] = Field(alias="durationMinutesExact", default=None, ge=1)
    duration_minutes_min: Optional[int] = Field(alias="durationMinutesMin", default=None, ge=1)
    duration_minutes_max: Optional[int] = Field(alias="durationMinutesMax", default=None, ge=1)
    # P1: scheduling style
    scheduling_style: str = Field(alias="schedulingStyle", default="balanced")
    # C1: computed target minutes (hard cap for planner)
    # Not required in create/update body — backend computes it
    target_minutes: Optional[int] = Field(alias="targetMinutes", default=None)

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class TaskCreate(TaskBase):
    locked_by_parent: bool = Field(alias="lockedByParent", default=False)
    created_by_role: str = Field(alias="createdByRole", default="student")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class TaskUpdate(TaskBase):
    locked_by_parent: bool = Field(alias="lockedByParent", default=False)

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class TaskSchema(TaskBase):
    id: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    progress_minutes: int = Field(alias="progressMinutes", default=0)
    locked_by_parent: bool = Field(alias="lockedByParent", default=False)
    created_by_role: str = Field(alias="createdByRole", default="student")
    # parent-task fields
    source: str = Field(default="student")
    locked: bool = Field(default=False)
    repeat: str = Field(default="none")
    child_can_delete: bool = Field(alias="childCanDelete", default=True)
    child_can_edit_core: bool = Field(alias="childCanEditCore", default=True)
    parent_id: Optional[str] = Field(alias="parentId", default=None)
    # target_minutes is always populated and returned
    target_minutes: int = Field(alias="targetMinutes", default=0)

    model_config = {"populate_by_name": True, "from_attributes": True, "serialize_by_alias": True}


class ParentTaskCreate(BaseModel):
    """Body for POST /api/parent/tasks — parent creates a task for a student."""
    student_id: str
    title: str
    subject: str = "Chung"
    description: Optional[str] = None
    deadline: Optional[str] = None
    estimated_minutes: int = 60
    priority: int = 2  # 1=low, 2=medium, 3=high
    locked: bool = False
    repeat: str = "none"  # none | daily | weekly
    scheduling_style: str = "balanced"

    model_config = {"populate_by_name": True}
