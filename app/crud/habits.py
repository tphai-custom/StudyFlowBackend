from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import Habit
from app.schemas.habit import HabitCreate


async def list_habits(db: AsyncSession, owner_user_id: str) -> list[Habit]:
    result = await db.execute(
        select(Habit).where(Habit.owner_user_id == owner_user_id).order_by(Habit.created_at)
    )
    return list(result.scalars().all())


async def get_habit(db: AsyncSession, habit_id: str) -> Optional[Habit]:
    result = await db.execute(select(Habit).where(Habit.id == habit_id))
    return result.scalar_one_or_none()


async def create_habit(db: AsyncSession, payload: HabitCreate, owner_user_id: str) -> Habit:
    data = payload.model_dump(by_alias=False)
    habit = Habit(
        id=str(uuid.uuid4()),
        **data,
        owner_user_id=owner_user_id,
        created_at=datetime.utcnow(),
    )
    db.add(habit)
    await db.flush()
    return habit


async def update_habit(db: AsyncSession, habit_id: str, payload: HabitCreate) -> Optional[Habit]:
    habit = await get_habit(db, habit_id)
    if habit is None:
        return None
    data = payload.model_dump(by_alias=False, exclude_unset=True)
    for key, value in data.items():
        setattr(habit, key, value)
    await db.flush()
    return habit


async def delete_habit(db: AsyncSession, habit_id: str) -> bool:
    result = await db.execute(delete(Habit).where(Habit.id == habit_id))
    return result.rowcount > 0
