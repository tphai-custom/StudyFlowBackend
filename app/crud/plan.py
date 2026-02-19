from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import PlanRecord
from app.schemas.plan import PlanRecordSchema


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
    # Serialize sessions with camelCase aliases so the frontend receives them correctly
    sessions_json = [
        s.model_dump(by_alias=True) if hasattr(s, "model_dump") else s
        for s in plan.sessions
    ]
    suggestions_json = [
        s.model_dump(by_alias=True) if hasattr(s, "model_dump") else s
        for s in plan.suggestions
    ]
    record = PlanRecord(
        id=plan.id or str(uuid.uuid4()),
        plan_version=plan.plan_version,
        sessions=sessions_json,
        unscheduled_tasks=plan.unscheduled_tasks,
        suggestions=suggestions_json,
        generated_at=plan.generated_at,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    await db.flush()
    return record


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
