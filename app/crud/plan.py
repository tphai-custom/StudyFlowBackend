from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import PlanRecord
from app.schemas.plan import PlanRecordSchema


def _to_json_safe(obj: Any) -> Any:
    """Recursively convert datetime/date objects to ISO strings so the value
    can be stored in a JSONB column without a serialisation error."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(v) for v in obj]
    return obj


async def get_plan_history(db: AsyncSession, owner_user_id: str, limit: int = 5) -> list[PlanRecord]:
    result = await db.execute(
        select(PlanRecord)
        .where(PlanRecord.owner_user_id == owner_user_id)
        .order_by(PlanRecord.created_at)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_latest_plan(db: AsyncSession, owner_user_id: str) -> Optional[PlanRecord]:
    result = await db.execute(
        select(PlanRecord)
        .where(PlanRecord.owner_user_id == owner_user_id)
        .order_by(PlanRecord.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def save_plan(db: AsyncSession, plan: PlanRecordSchema) -> PlanRecord:
    # Serialize sessions with camelCase aliases so the frontend receives them correctly.
    # Use mode='json' (Pydantic v2) so datetime fields become ISO strings; fall back to
    # the recursive _to_json_safe helper for plain dicts that may also carry datetimes.
    sessions_json = _to_json_safe([
        s.model_dump(by_alias=True, mode="json") if hasattr(s, "model_dump") else s
        for s in plan.sessions
    ])
    suggestions_json = _to_json_safe([
        s.model_dump(by_alias=True, mode="json") if hasattr(s, "model_dump") else s
        for s in plan.suggestions
    ])
    record = PlanRecord(
        id=plan.id or str(uuid.uuid4()),
        plan_version=plan.plan_version,
        sessions=sessions_json,
        unscheduled_tasks=_to_json_safe(plan.unscheduled_tasks),
        suggestions=suggestions_json,
        generated_at=plan.generated_at,
        owner_user_id=plan.owner_user_id,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    await db.flush()
    return record


async def remove_habit_from_plans(db: AsyncSession, habit_id: str, owner_user_id: str) -> None:
    """Remove all sessions referencing *habit_id* from every stored plan record."""
    result = await db.execute(select(PlanRecord).where(PlanRecord.owner_user_id == owner_user_id))
    records: list[PlanRecord] = list(result.scalars().all())
    for record in records:
        new_sessions = [
            s for s in (record.sessions or [])
            if s.get("habitId") != habit_id
        ]
        if new_sessions != record.sessions:
            record.sessions = new_sessions
    await db.flush()


async def remove_task_from_plans(db: AsyncSession, task_id: str, owner_user_id: str) -> None:
    """Remove all sessions and unscheduled_task entries referencing *task_id*
    from every stored plan record."""
    result = await db.execute(select(PlanRecord).where(PlanRecord.owner_user_id == owner_user_id))
    records: list[PlanRecord] = list(result.scalars().all())
    for record in records:
        new_sessions = [
            s for s in (record.sessions or [])
            if s.get("taskId") != task_id
        ]
        new_unscheduled = [
            t for t in (record.unscheduled_tasks or [])
            if t.get("id") != task_id
        ]
        if new_sessions != record.sessions or new_unscheduled != record.unscheduled_tasks:
            record.sessions = new_sessions
            record.unscheduled_tasks = new_unscheduled
    await db.flush()


async def update_session_status(
    db: AsyncSession, session_id: str, status: str, owner_user_id: str
) -> Optional[PlanRecord]:
    plan = await get_latest_plan(db, owner_user_id)
    if plan is None:
        return None
    sessions = list(plan.sessions)
    found = False
    for i, session in enumerate(sessions):
        if session.get("id") == session_id:
            sessions[i] = {
                **session,
                "status": status,
                "completedAt": datetime.utcnow().isoformat() if status == "done" else None,
            }
            found = True
            break
    if not found:
        return None  # session not found
    plan.sessions = sessions
    await db.flush()

    # --- Recompute task progress_minutes after session status change ---
    from app.models.task import Task
    from sqlalchemy import select as sa_select

    # Collect all task_ids that have sessions in this plan
    task_minutes: dict[str, int] = {}
    for s in sessions:
        tid = s.get("taskId") or s.get("task_id")
        if not tid or s.get("source") == "break":
            continue
        if s.get("status") == "done":
            task_minutes[tid] = task_minutes.get(tid, 0) + (s.get("minutes") or 0)
        else:
            # ensure task appears with 0 if not already set
            if tid not in task_minutes:
                task_minutes[tid] = 0

    # Update affected tasks
    if task_minutes:
        task_result = await db.execute(
            sa_select(Task).where(
                Task.owner_user_id == owner_user_id,
                Task.id.in_(list(task_minutes.keys())),
            )
        )
        tasks_to_update = list(task_result.scalars().all())
        for task in tasks_to_update:
            task.progress_minutes = task_minutes.get(task.id, 0)
        await db.flush()

    return plan


async def get_task_progress(
    db: AsyncSession, task_id: str, owner_user_id: str
) -> dict:
    """Compute live task progress from latest plan sessions."""
    from app.models.task import Task
    from sqlalchemy import select as sa_select

    plan = await get_latest_plan(db, owner_user_id)
    task_result = await db.execute(
        sa_select(Task).where(Task.id == task_id, Task.owner_user_id == owner_user_id)
    )
    task = task_result.scalar_one_or_none()
    if not task:
        return {}

    done_minutes = 0
    total_sessions = 0
    done_sessions = 0
    planned_minutes = task.estimated_minutes or 1

    if plan:
        for s in (plan.sessions or []):
            tid = s.get("taskId") or s.get("task_id")
            if tid != task_id or s.get("source") == "break":
                continue
            total_sessions += 1
            if s.get("status") == "done":
                done_sessions += 1
                done_minutes += s.get("minutes", 0)

    if total_sessions > 0:
        planned_minutes = sum(
            s.get("minutes", 0)
            for s in (plan.sessions or [])
            if (s.get("taskId") or s.get("task_id")) == task_id and s.get("source") != "break"
        )
        planned_minutes = max(planned_minutes, 1)

    progress_percent = round(done_minutes / planned_minutes * 100) if planned_minutes > 0 else 0
    progress_percent = min(100, progress_percent)

    return {
        "task_id": task_id,
        "planned_minutes": planned_minutes,
        "done_minutes": done_minutes,
        "progress_percent": progress_percent,
        "sessions_done": done_sessions,
        "total_sessions": total_sessions,
    }


async def toggle_session_lock(
    db: AsyncSession, session_id: str, locked: bool, owner_user_id: str
) -> Optional[PlanRecord]:
    """Toggle the `locked` flag on a session in the latest plan."""
    plan = await get_latest_plan(db, owner_user_id)
    if plan is None:
        return None
    sessions = list(plan.sessions)
    found = False
    for i, session in enumerate(sessions):
        if session.get("id") == session_id:
            sessions[i] = {**session, "locked": locked}
            found = True
            break
    if not found:
        return None
    plan.sessions = sessions
    await db.flush()
    return plan
