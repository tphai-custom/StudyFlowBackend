from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


def compute_target_minutes(
    duration_mode: str,
    exact: Optional[int],
    t_min: Optional[int],
    t_max: Optional[int],
    estimated_minutes: int,
) -> int:
    """C2: Compute the hard-cap target minutes for the planner.

    exact  → target = exact_minutes
    estimate → base = round((min+max)/2), target = clamp(base, min, max)
    fallback → estimated_minutes
    """
    if duration_mode == "exact" and exact and exact > 0:
        return exact
    if duration_mode == "estimate" and t_min and t_max and t_min > 0 and t_max > 0:
        base = round((t_min + t_max) / 2)
        return max(t_min, min(t_max, base))
    return estimated_minutes


async def list_tasks(db: AsyncSession, owner_user_id: str) -> list[Task]:
    result = await db.execute(
        select(Task)
        .where(Task.owner_user_id == owner_user_id, Task.deleted_at.is_(None))
        .order_by(Task.created_at)
    )
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: str) -> Optional[Task]:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def create_task(db: AsyncSession, payload: TaskCreate, owner_user_id: str) -> Task:
    data = payload.model_dump(by_alias=False)
    # Remove target_minutes from payload if present — we compute it
    data.pop("target_minutes", None)
    target = compute_target_minutes(
        data.get("duration_mode", "estimate"),
        data.get("duration_minutes_exact"),
        data.get("duration_minutes_min"),
        data.get("duration_minutes_max"),
        data.get("estimated_minutes", 60),
    )
    task = Task(
        id=str(uuid.uuid4()),
        **data,
        owner_user_id=owner_user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        progress_minutes=0,
        target_minutes=target,
    )
    db.add(task)
    await db.flush()
    return task


async def update_task(db: AsyncSession, task_id: str, payload: TaskUpdate) -> Optional[Task]:
    task = await get_task(db, task_id)
    if task is None:
        return None
    data = payload.model_dump(by_alias=False, exclude_unset=True)
    data.pop("target_minutes", None)  # always recomputed
    for key, value in data.items():
        setattr(task, key, value)
    # Recompute target_minutes after potential duration field updates
    task.target_minutes = compute_target_minutes(
        task.duration_mode,
        task.duration_minutes_exact,
        task.duration_minutes_min,
        task.duration_minutes_max,
        task.estimated_minutes,
    )
    task.updated_at = datetime.utcnow()
    await db.flush()
    return task


async def delete_task(db: AsyncSession, task_id: str) -> bool:
    result = await db.execute(delete(Task).where(Task.id == task_id))
    return result.rowcount > 0


async def update_task_progress(db: AsyncSession, task_id: str, progress_minutes: int) -> Optional[Task]:
    task = await get_task(db, task_id)
    if task is None:
        return None
    task.progress_minutes = progress_minutes
    task.updated_at = datetime.utcnow()
    await db.flush()
    return task


async def create_parent_task(
    db: AsyncSession,
    parent_id: str,
    student_id: str,
    title: str,
    subject: str = "Chung",
    description: Optional[str] = None,
    deadline: Optional[str] = None,
    estimated_minutes: int = 60,
    priority: int = 2,
    locked: bool = False,
    repeat: str = "none",
) -> Task:
    """Parent creates a task directly in the student's tasks table."""
    from datetime import timezone as _tz
    now = datetime.now(_tz.utc)
    deadline_str = deadline or (now.date().isoformat() + "T23:59")
    importance_map = {1: 1, 2: 2, 3: 3}
    task = Task(
        id=str(uuid.uuid4()),
        subject=subject,
        title=title,
        deadline=deadline_str,
        timezone="Asia/Ho_Chi_Minh",
        difficulty=priority,
        duration_estimate_min=estimated_minutes,
        duration_estimate_max=estimated_minutes,
        duration_unit="minutes",
        estimated_minutes=estimated_minutes,
        importance=importance_map.get(priority, 2),
        content_focus=description,
        success_criteria=[],
        notes=description,
        progress_minutes=0,
        locked_by_parent=locked,
        locked=locked,
        created_by_role="parent",
        source="parent",
        repeat=repeat,
        child_can_delete=False,
        child_can_edit_core=not locked,
        parent_id=parent_id,
        owner_user_id=student_id,
        created_at=now,
        updated_at=now,
        target_minutes=estimated_minutes,
    )
    db.add(task)
    await db.flush()
    return task


async def get_task_progress(db: AsyncSession, task_id: str, owner_user_id: str) -> dict:
    """Compute task progress from plan sessions."""
    from app.crud import plan as plan_crud
    from app.models.plan import PlanRecord
    from sqlalchemy import select as sa_select

    task = await get_task(db, task_id)
    if not task or task.owner_user_id != owner_user_id:
        return {}

    plan_result = await db.execute(
        sa_select(PlanRecord)
        .where(PlanRecord.owner_user_id == owner_user_id)
        .order_by(PlanRecord.created_at.desc())
        .limit(1)
    )
    plan = plan_result.scalar_one_or_none()

    done_minutes = 0
    planned_minutes = 0
    done_sessions = 0
    total_sessions = 0

    if plan and plan.sessions:
        for s in plan.sessions:
            if s.get("taskId") == task_id or s.get("task_id") == task_id:
                mins = s.get("minutes", 0)
                planned_minutes += mins
                total_sessions += 1
                if s.get("status") == "done":
                    done_minutes += mins
                    done_sessions += 1

    if planned_minutes == 0:
        planned_minutes = task.estimated_minutes

    progress_percent = round(done_minutes / planned_minutes * 100) if planned_minutes > 0 else 0

    return {
        "task_id": task_id,
        "done_minutes": done_minutes,
        "planned_minutes": planned_minutes,
        "progress_percent": progress_percent,
        "done_sessions": done_sessions,
        "total_sessions": total_sessions,
    }
