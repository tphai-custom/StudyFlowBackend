"""CRUD helpers for parent-assigned tasks, habits, ideas, and parent settings."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assigned import (
    HabitTick,
    ParentAssignedHabit,
    ParentAssignedTask,
    ParentIdea,
    ParentSettings,
    ParentTaskItem,
    TaskUpdate,
)
from app.schemas.assigned import (
    AssignedHabitCreate,
    AssignedHabitUpdate,
    AssignedTaskCreate,
    AssignedTaskUpdate,
    HabitTickCreate,
    IdeaCreate,
    ParentSettingsUpdate,
    TaskItemCreate,
    TaskItemUpdate,
    TaskUpdateCreate,
)


# ── Assigned Tasks ────────────────────────────────────────────────────────────

async def create_assigned_task(
    db: AsyncSession,
    parent_id: str,
    student_id: str,
    data: AssignedTaskCreate,
) -> ParentAssignedTask:
    task = ParentAssignedTask(
        id=str(uuid.uuid4()),
        parent_id=parent_id,
        student_id=student_id,
        title=data.title,
        subject=data.subject,
        description=data.description,
        deadline=data.deadline,
        priority=data.priority,
        tag=data.tag,
        locked=data.locked,
        type="TASK",
        status="ASSIGNED",
    )
    db.add(task)
    await db.flush()
    return task


async def get_assigned_task(
    db: AsyncSession, task_id: str
) -> Optional[ParentAssignedTask]:
    result = await db.execute(
        select(ParentAssignedTask).where(ParentAssignedTask.id == task_id)
    )
    return result.scalar_one_or_none()


async def list_assigned_tasks_for_parent(
    db: AsyncSession, parent_id: str, student_id: str
) -> list[ParentAssignedTask]:
    result = await db.execute(
        select(ParentAssignedTask)
        .where(
            ParentAssignedTask.parent_id == parent_id,
            ParentAssignedTask.student_id == student_id,
        )
        .order_by(ParentAssignedTask.created_at.desc())
    )
    return list(result.scalars().all())


async def list_assigned_tasks_for_student(
    db: AsyncSession, student_id: str
) -> list[ParentAssignedTask]:
    result = await db.execute(
        select(ParentAssignedTask)
        .where(
            ParentAssignedTask.student_id == student_id,
            ParentAssignedTask.status.notin_(["ARCHIVED"]),
        )
        .order_by(ParentAssignedTask.created_at.desc())
    )
    return list(result.scalars().all())


async def update_assigned_task(
    db: AsyncSession, task: ParentAssignedTask, data: AssignedTaskUpdate
) -> ParentAssignedTask:
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(task, field, val)
    await db.flush()
    return task


async def student_update_task(
    db: AsyncSession,
    task: ParentAssignedTask,
    student_note: Optional[str],
    reschedule_date: Optional[str],
    reschedule_reason: Optional[str],
) -> ParentAssignedTask:
    if student_note is not None:
        task.student_note = student_note
    if reschedule_date is not None:
        task.reschedule_requested_date = reschedule_date
    if reschedule_reason is not None:
        task.reschedule_reason = reschedule_reason
    await db.flush()
    return task


# ── Assigned Habits ───────────────────────────────────────────────────────────

async def create_assigned_habit(
    db: AsyncSession,
    parent_id: str,
    student_id: str,
    data: AssignedHabitCreate,
) -> ParentAssignedHabit:
    habit = ParentAssignedHabit(
        id=str(uuid.uuid4()),
        parent_id=parent_id,
        student_id=student_id,
        name=data.name,
        frequency_type=data.frequency_type,
        frequency_value=data.frequency_value,
        minutes=data.minutes,
        suggested_time=data.suggested_time,
        locked=data.locked,
        status="active",
    )
    db.add(habit)
    await db.flush()
    return habit


async def get_assigned_habit(
    db: AsyncSession, habit_id: str
) -> Optional[ParentAssignedHabit]:
    result = await db.execute(
        select(ParentAssignedHabit).where(ParentAssignedHabit.id == habit_id)
    )
    return result.scalar_one_or_none()


async def list_assigned_habits_for_parent(
    db: AsyncSession, parent_id: str, student_id: str
) -> list[ParentAssignedHabit]:
    result = await db.execute(
        select(ParentAssignedHabit)
        .where(
            ParentAssignedHabit.parent_id == parent_id,
            ParentAssignedHabit.student_id == student_id,
        )
        .order_by(ParentAssignedHabit.created_at.desc())
    )
    return list(result.scalars().all())


async def list_assigned_habits_for_student(
    db: AsyncSession, student_id: str
) -> list[ParentAssignedHabit]:
    result = await db.execute(
        select(ParentAssignedHabit)
        .where(
            ParentAssignedHabit.student_id == student_id,
            ParentAssignedHabit.status == "active",
        )
        .order_by(ParentAssignedHabit.created_at.desc())
    )
    return list(result.scalars().all())


async def update_assigned_habit(
    db: AsyncSession, habit: ParentAssignedHabit, data: AssignedHabitUpdate
) -> ParentAssignedHabit:
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(habit, field, val)
    await db.flush()
    return habit


async def tick_habit(
    db: AsyncSession,
    habit_id: str,
    student_id: str,
    data: HabitTickCreate,
) -> HabitTick:
    # Upsert: if already ticked today, update; else insert
    result = await db.execute(
        select(HabitTick).where(
            HabitTick.habit_id == habit_id,
            HabitTick.student_id == student_id,
            HabitTick.date == data.date,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.completed = True
        existing.note = data.note
        await db.flush()
        return existing

    tick = HabitTick(
        id=str(uuid.uuid4()),
        habit_id=habit_id,
        student_id=student_id,
        date=data.date,
        completed=True,
        note=data.note,
    )
    db.add(tick)
    await db.flush()
    return tick


async def list_habit_ticks(
    db: AsyncSession, habit_id: str
) -> list[HabitTick]:
    result = await db.execute(
        select(HabitTick).where(HabitTick.habit_id == habit_id)
        .order_by(HabitTick.date.desc())
    )
    return list(result.scalars().all())


# ── Ideas ─────────────────────────────────────────────────────────────────────

async def create_idea(
    db: AsyncSession,
    parent_id: str,
    student_id: str,
    data: IdeaCreate,
) -> ParentIdea:
    idea = ParentIdea(
        id=str(uuid.uuid4()),
        parent_id=parent_id,
        student_id=student_id,
        content=data.content,
        suggested_type=data.suggested_type,
        status="pending",
    )
    db.add(idea)
    await db.flush()
    return idea


async def get_idea(db: AsyncSession, idea_id: str) -> Optional[ParentIdea]:
    result = await db.execute(select(ParentIdea).where(ParentIdea.id == idea_id))
    return result.scalar_one_or_none()


async def list_ideas_for_student(
    db: AsyncSession, student_id: str
) -> list[ParentIdea]:
    result = await db.execute(
        select(ParentIdea)
        .where(ParentIdea.student_id == student_id, ParentIdea.status == "pending")
        .order_by(ParentIdea.created_at.desc())
    )
    return list(result.scalars().all())


# ── Parent Settings ───────────────────────────────────────────────────────────

async def get_or_create_parent_settings(
    db: AsyncSession, parent_id: str
) -> ParentSettings:
    result = await db.execute(
        select(ParentSettings).where(ParentSettings.parent_id == parent_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        s = ParentSettings(id=str(uuid.uuid4()), parent_id=parent_id)
        db.add(s)
        await db.flush()
    return s


async def update_parent_settings(
    db: AsyncSession, settings: ParentSettings, data: ParentSettingsUpdate
) -> ParentSettings:
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(settings, field, val)
    await db.flush()
    return settings


# ── Parent Task Items (checklist) ─────────────────────────────────────────────

async def create_task_item(
    db: AsyncSession, task_id: str, data: TaskItemCreate
) -> ParentTaskItem:
    item = ParentTaskItem(
        id=str(uuid.uuid4()),
        task_id=task_id,
        label=data.label,
        subject=data.subject,
        order_index=data.order_index,
        is_done=False,
    )
    db.add(item)
    await db.flush()
    return item


async def list_task_items(
    db: AsyncSession, task_id: str
) -> list[ParentTaskItem]:
    result = await db.execute(
        select(ParentTaskItem)
        .where(ParentTaskItem.task_id == task_id)
        .order_by(ParentTaskItem.order_index, ParentTaskItem.created_at)
    )
    return list(result.scalars().all())


async def get_task_item(
    db: AsyncSession, item_id: str
) -> Optional[ParentTaskItem]:
    result = await db.execute(
        select(ParentTaskItem).where(ParentTaskItem.id == item_id)
    )
    return result.scalar_one_or_none()


async def update_task_item(
    db: AsyncSession,
    item: ParentTaskItem,
    data: TaskItemUpdate,
    actor_role: str = "student",
) -> ParentTaskItem:
    if data.is_done is not None:
        item.is_done = data.is_done
        if data.is_done:
            item.done_at = datetime.now(timezone.utc)
            item.done_by = actor_role
        else:
            item.done_at = None
            item.done_by = None
    if data.label is not None:
        item.label = data.label
    if data.subject is not None:
        item.subject = data.subject
    await db.flush()
    return item


# ── Task Updates (activity log) ───────────────────────────────────────────────

async def create_task_update(
    db: AsyncSession, task_id: str, actor_role: str, data: TaskUpdateCreate
) -> TaskUpdate:
    upd = TaskUpdate(
        id=str(uuid.uuid4()),
        task_id=task_id,
        actor_role=actor_role,
        type=data.type,
        content=data.content,
    )
    db.add(upd)
    await db.flush()
    return upd


async def list_task_updates(
    db: AsyncSession, task_id: str
) -> list[TaskUpdate]:
    result = await db.execute(
        select(TaskUpdate)
        .where(TaskUpdate.task_id == task_id)
        .order_by(TaskUpdate.created_at.desc())
    )
    return list(result.scalars().all())


# ── Habit with status helpers ─────────────────────────────────────────────────

def _tz_today(tz_str: str = "Asia/Ho_Chi_Minh") -> str:
    """Return YYYY-MM-DD for today in given timezone (no pytz dependency)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(tz_str)).strftime("%Y-%m-%d")
    except Exception:
        return date.today().isoformat()


async def get_habit_ticked_today(
    db: AsyncSession, habit_id: str, student_id: str, today_str: str
) -> Optional[HabitTick]:
    result = await db.execute(
        select(HabitTick).where(
            HabitTick.habit_id == habit_id,
            HabitTick.student_id == student_id,
            HabitTick.date == today_str,
        )
    )
    return result.scalar_one_or_none()


async def compute_habit_streak_and_days(
    db: AsyncSession, habit_id: str, student_id: str, today_str: str
) -> tuple[int, list[dict]]:
    """Return (streak_count, last_7_days).

    streak: consecutive days up to yesterday (or today if already ticked).
    last_7_days: [{date, done}, ...] newest-first.
    """
    result = await db.execute(
        select(HabitTick.date)
        .where(HabitTick.habit_id == habit_id, HabitTick.student_id == student_id, HabitTick.completed == True)  # noqa: E712
        .order_by(HabitTick.date.desc())
    )
    ticked_dates: set[str] = {row[0] for row in result.all()}

    today = date.fromisoformat(today_str)

    # 7-day window
    last_7: list[dict] = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        last_7.append({"date": d, "done": d in ticked_dates})

    # Streak: count backwards from today
    streak = 0
    check = today
    while True:
        ds = check.isoformat()
        if ds in ticked_dates:
            streak += 1
            check = check - timedelta(days=1)
        else:
            # Allow one "grace" for today not yet ticked — count from yesterday
            if ds == today_str and streak == 0:
                check = check - timedelta(days=1)
                continue
            break

    return streak, last_7
