from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


async def list_tasks(db: AsyncSession, owner_user_id: str) -> list[Task]:
    result = await db.execute(
        select(Task).where(Task.owner_user_id == owner_user_id).order_by(Task.created_at)
    )
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: str) -> Optional[Task]:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def create_task(db: AsyncSession, payload: TaskCreate, owner_user_id: str) -> Task:
    data = payload.model_dump(by_alias=False)
    task = Task(
        id=str(uuid.uuid4()),
        **data,
        owner_user_id=owner_user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        progress_minutes=0,
    )
    db.add(task)
    await db.flush()
    return task


async def update_task(db: AsyncSession, task_id: str, payload: TaskUpdate) -> Optional[Task]:
    task = await get_task(db, task_id)
    if task is None:
        return None
    data = payload.model_dump(by_alias=False, exclude_unset=True)
    for key, value in data.items():
        setattr(task, key, value)
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
