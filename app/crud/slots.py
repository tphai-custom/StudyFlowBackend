from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.free_slot import FreeSlot
from app.schemas.free_slot import FreeSlotCreate


async def list_slots(db: AsyncSession) -> list[FreeSlot]:
    result = await db.execute(select(FreeSlot).order_by(FreeSlot.weekday, FreeSlot.start_time))
    return list(result.scalars().all())


async def get_slot(db: AsyncSession, slot_id: str) -> Optional[FreeSlot]:
    result = await db.execute(select(FreeSlot).where(FreeSlot.id == slot_id))
    return result.scalar_one_or_none()


def _calc_capacity(start: str, end: str) -> int:
    sh, sm = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))
    return (eh * 60 + em) - (sh * 60 + sm)


async def create_slot(db: AsyncSession, payload: FreeSlotCreate) -> FreeSlot:
    data = payload.model_dump(by_alias=False)
    capacity = _calc_capacity(data["start_time"], data["end_time"])
    if capacity <= 0:
        raise ValueError("Giờ kết thúc phải sau giờ bắt đầu")
    slot = FreeSlot(
        id=str(uuid.uuid4()),
        **data,
        capacity_minutes=capacity,
        created_at=datetime.utcnow(),
    )
    db.add(slot)
    await db.flush()
    return slot


async def update_slot(db: AsyncSession, slot_id: str, payload: FreeSlotCreate) -> Optional[FreeSlot]:
    slot = await get_slot(db, slot_id)
    if slot is None:
        return None
    data = payload.model_dump(by_alias=False, exclude_unset=True)
    for key, value in data.items():
        setattr(slot, key, value)
    slot.capacity_minutes = _calc_capacity(slot.start_time, slot.end_time)
    await db.flush()
    return slot


async def delete_slot(db: AsyncSession, slot_id: str) -> bool:
    result = await db.execute(delete(FreeSlot).where(FreeSlot.id == slot_id))
    return result.rowcount > 0
