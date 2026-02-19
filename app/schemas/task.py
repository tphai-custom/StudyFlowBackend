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

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class TaskCreate(TaskBase):
    pass


class TaskUpdate(TaskBase):
    pass


class TaskSchema(TaskBase):
    id: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    progress_minutes: int = Field(alias="progressMinutes", default=0)

    model_config = {"populate_by_name": True, "from_attributes": True, "serialize_by_alias": True}
