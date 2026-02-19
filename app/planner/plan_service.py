"""Port of planService.ts — orchestrate planner with feedback tuning."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import feedback as feedback_crud
from app.crud import habits as habits_crud
from app.crud import plan as plan_crud
from app.crud import profile as profile_crud
from app.crud import settings as settings_crud
from app.crud import slots as slots_crud
from app.crud import tasks as tasks_crud
from app.planner.generate_plan import generate_plan
from app.schemas.free_slot import FreeSlotSchema
from app.schemas.habit import HabitSchema
from app.schemas.plan import PlanRecordSchema
from app.schemas.settings import AppSettingsSchema
from app.schemas.task import TaskSchema


def _model_to_task(t) -> TaskSchema:
    return TaskSchema(
        id=t.id,
        subject=t.subject,
        title=t.title,
        deadline=t.deadline,
        timezone=t.timezone,
        difficulty=t.difficulty,
        durationEstimateMin=t.duration_estimate_min,
        durationEstimateMax=t.duration_estimate_max,
        durationUnit=t.duration_unit,
        estimatedMinutes=t.estimated_minutes,
        importance=t.importance,
        contentFocus=t.content_focus,
        successCriteria=t.success_criteria or [],
        milestones=t.milestones,
        notes=t.notes,
        createdAt=t.created_at,
        updatedAt=t.updated_at,
        progressMinutes=t.progress_minutes,
    )


def _model_to_slot(s) -> FreeSlotSchema:
    return FreeSlotSchema(
        id=s.id,
        weekday=s.weekday,
        startTime=s.start_time,
        endTime=s.end_time,
        capacityMinutes=s.capacity_minutes,
        source=s.source,
        createdAt=s.created_at,
    )


def _model_to_habit(h) -> HabitSchema:
    return HabitSchema(
        id=h.id,
        name=h.name,
        cadence=h.cadence,
        weekday=h.weekday,
        minutes=h.minutes,
        preset=h.preset,
        preferredStart=h.preferred_start,
        energyWindow=h.energy_window,
        createdAt=h.created_at,
    )


async def _tune_settings_with_feedback(db: AsyncSession) -> AppSettingsSchema:
    settings_row = await settings_crud.get_settings(db)
    feedback_list = await feedback_crud.list_feedback(db)

    settings = AppSettingsSchema(
        id=settings_row.id,
        dailyLimitMinutes=settings_row.daily_limit_minutes,
        bufferPercent=settings_row.buffer_percent,
        breakPreset=settings_row.break_preset,
        timezone=settings_row.timezone,
        lastUpdated=settings_row.last_updated,
    )

    if not feedback_list:
        return settings

    latest = feedback_list[-1]
    if latest.label == "too_dense":
        settings.buffer_percent = min(0.5, settings.buffer_percent + 0.1)
    elif latest.label == "too_easy":
        settings.buffer_percent = max(0.05, settings.buffer_percent - 0.05)
    elif latest.label == "need_more_time":
        settings.daily_limit_minutes = min(600, settings.daily_limit_minutes + 30)

    return settings


async def rebuild_plan(db: AsyncSession) -> Optional[PlanRecordSchema]:
    tasks_rows = await tasks_crud.list_tasks(db)
    slots_rows = await slots_crud.list_slots(db)

    if not tasks_rows or not slots_rows:
        return None

    habits_rows = await habits_crud.list_habits(db)
    settings = await _tune_settings_with_feedback(db)
    latest_plan = await plan_crud.get_latest_plan(db)

    tasks = [_model_to_task(t) for t in tasks_rows]
    free_slots = [_model_to_slot(s) for s in slots_rows]
    habits = [_model_to_habit(h) for h in habits_rows]

    plan = generate_plan(
        tasks=tasks,
        free_slots=free_slots,
        habits=habits,
        settings=settings,
        now_iso=datetime.now(timezone.utc).isoformat(),
        previous_plan_version=latest_plan.plan_version if latest_plan else None,
    )

    await plan_crud.save_plan(db, plan)
    return plan
