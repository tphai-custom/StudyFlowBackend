"""CRUD for plan_overrides table."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan_override import PlanOverride
from app.schemas.plan_override import PlanOverrideCreate


async def get_override(db: AsyncSession, user_id: str) -> Optional[PlanOverride]:
    result = await db.execute(
        select(PlanOverride)
        .where(PlanOverride.user_id == user_id)
        .order_by(PlanOverride.updated_at.desc())
    )
    return result.scalar_one_or_none()


async def upsert_override(
    db: AsyncSession,
    user_id: str,
    payload: PlanOverrideCreate,
    admin_id: str,
) -> PlanOverride:
    """Create a new override record (one per save - simple append-style log)."""
    override = PlanOverride(
        id=str(uuid.uuid4()),
        user_id=user_id,
        plan_id=payload.plan_id,
        date_start=payload.date_start,
        date_end=payload.date_end,
        payload=payload.payload,
        edited_by=admin_id,
    )
    db.add(override)
    await db.flush()
    return override
