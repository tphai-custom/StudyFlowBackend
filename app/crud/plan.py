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


async def get_plan_history(db: AsyncSession, limit: int = 5) -> list[PlanRecord]:
    result = await db.execute(
        select(PlanRecord).order_by(PlanRecord.created_at).limit(limit)
    )
    return list(result.scalars().all())


async def get_latest_plan(db: AsyncSession) -> Optional[PlanRecord]:
    result = await db.execute(
        select(PlanRecord).order_by(PlanRecord.created_at.desc()).limit(1)
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
        created_at=datetime.utcnow(),
    )
    db.add(record)
    await db.flush()
    return record


async def remove_habit_from_plans(db: AsyncSession, habit_id: str) -> None:
    """Remove all sessions referencing *habit_id* from every stored plan record."""
    result = await db.execute(select(PlanRecord))
    records: list[PlanRecord] = list(result.scalars().all())
    for record in records:
        new_sessions = [
            s for s in (record.sessions or [])
            if s.get("habitId") != habit_id
        ]
        if new_sessions != record.sessions:
            record.sessions = new_sessions
    await db.flush()


async def remove_task_from_plans(db: AsyncSession, task_id: str) -> None:
    """Remove all sessions and unscheduled_task entries referencing *task_id*
    from every stored plan record."""
    result = await db.execute(select(PlanRecord))
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
    db: AsyncSession, session_id: str, status: str
) -> Optional[PlanRecord]:
    plan = await get_latest_plan(db)
    if plan is None:
        return None
    sessions = list(plan.sessions)
    for i, session in enumerate(sessions):
        if session.get("id") == session_id:
            sessions[i] = {
                **session,
                "status": status,
                "completedAt": datetime.utcnow().isoformat() if status == "done" else None,
            }
            break
    else:
        return None  # session not found
    plan.sessions = sessions
    await db.flush()
    return plan
