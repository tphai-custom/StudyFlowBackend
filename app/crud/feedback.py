from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackAdminUpdate, FeedbackCreate


async def list_feedback(db: AsyncSession, owner_user_id: str) -> list[Feedback]:
    result = await db.execute(
        select(Feedback)
        .where(Feedback.owner_user_id == owner_user_id)
        .order_by(Feedback.submitted_at)
    )
    return list(result.scalars().all())


async def list_feedback_by_user(db: AsyncSession, owner_user_id: str) -> list[Feedback]:
    """Admin: list all feedback for a specific user."""
    result = await db.execute(
        select(Feedback)
        .where(Feedback.owner_user_id == owner_user_id)
        .order_by(Feedback.submitted_at.desc())
    )
    return list(result.scalars().all())


async def save_feedback(db: AsyncSession, payload: FeedbackCreate, owner_user_id: str) -> Feedback:
    data = payload.model_dump(by_alias=False)
    fb = Feedback(
        id=str(uuid.uuid4()),
        **data,
        owner_user_id=owner_user_id,
        status="open",
        submitted_at=datetime.utcnow(),
    )
    db.add(fb)
    await db.flush()
    return fb


async def admin_update_feedback(
    db: AsyncSession, feedback_id: str, payload: FeedbackAdminUpdate
) -> Optional[Feedback]:
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    fb = result.scalar_one_or_none()
    if not fb:
        return None
    if payload.status is not None:
        fb.status = payload.status
    if payload.admin_reply is not None:
        fb.admin_reply = payload.admin_reply
    await db.flush()
    return fb

