from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate


async def list_feedback(db: AsyncSession) -> list[Feedback]:
    result = await db.execute(select(Feedback).order_by(Feedback.submitted_at))
    return list(result.scalars().all())


async def save_feedback(db: AsyncSession, payload: FeedbackCreate) -> Feedback:
    data = payload.model_dump(by_alias=False)
    fb = Feedback(
        id=str(uuid.uuid4()),
        **data,
        submitted_at=datetime.utcnow(),
    )
    db.add(fb)
    await db.flush()
    return fb
