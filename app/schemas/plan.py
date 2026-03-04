from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, Field


class SessionSchema(BaseModel):
    id: str
    task_id: Optional[str] = Field(alias="taskId", default=None)
    habit_id: Optional[str] = Field(alias="habitId", default=None)
    source: Literal["task", "habit", "break"]
    # B1: canonical session type — STUDY, HABIT, BREAK
    session_type: Literal["STUDY", "HABIT", "BREAK"] = Field(alias="sessionType", default="STUDY")
    source_type: Optional[str] = Field(alias="sourceType", default=None)  # "self_task" | "parent_task"
    badge_label: Optional[str] = Field(alias="badgeLabel", default=None)  # e.g. "Phụ huynh giao 🔒"
    locked_by_parent: Optional[bool] = Field(alias="lockedByParent", default=None)
    subject: str
    title: str
    planned_start: str = Field(alias="plannedStart")
    planned_end: str = Field(alias="plannedEnd")
    minutes: int
    # C4: study_minutes = actual study time (no buffer); occupied_minutes = calendar time (with buffer)
    study_minutes: int = Field(alias="studyMinutes", default=0)
    occupied_minutes: int = Field(alias="occupiedMinutes", default=0)
    buffer_minutes: int = Field(alias="bufferMinutes", default=0)
    status: Literal["pending", "done", "skipped", "auto"] = "pending"
    locked: bool = False
    checklist: Optional[list[str]] = None
    success_criteria: Optional[list[str]] = Field(alias="successCriteria", default=None)
    milestone_title: Optional[str] = Field(alias="milestoneTitle", default=None)
    completed_at: Optional[str] = Field(alias="completedAt", default=None)
    plan_version: int = Field(alias="planVersion")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class SessionStatusUpdate(BaseModel):
    status: Literal["pending", "done", "skipped"]


class PlanSuggestionSchema(BaseModel):
    type: Literal[
        "increase_free_time",
        "reduce_duration",
        "extend_deadline",
        "reduce_buffer",
        "adjust_daily_limit",
    ]
    message: str


class PlanRecordSchema(BaseModel):
    id: str
    plan_version: int = Field(alias="planVersion")
    sessions: list  # raw dicts or SessionSchema – stored/returned as camelCase
    unscheduled_tasks: list = Field(alias="unscheduledTasks", default_factory=list)
    suggestions: list[PlanSuggestionSchema] = Field(default_factory=list)
    generated_at: str = Field(alias="generatedAt")
    owner_user_id: Optional[str] = None

    model_config = {"populate_by_name": True, "from_attributes": True, "serialize_by_alias": True}
