"""CRUD helpers for exchange messages."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange import ExchangeMessage


async def create_message(
    db: AsyncSession,
    parent_id: str,
    student_id: str,
    content: str,
    tag: str = "other",
    sender_role: str = "parent",
) -> ExchangeMessage:
    msg = ExchangeMessage(
        id=str(uuid.uuid4()),
        parent_id=parent_id,
        student_id=student_id,
        sender_role=sender_role,
        tag=tag,
        content=content,
        status="unread",
        pinned=False,
    )
    db.add(msg)
    await db.flush()
    return msg


async def list_messages_for_parent(
    db: AsyncSession, parent_id: str, student_id: str
) -> list[ExchangeMessage]:
    result = await db.execute(
        select(ExchangeMessage)
        .where(
            ExchangeMessage.parent_id == parent_id,
            ExchangeMessage.student_id == student_id,
        )
        .order_by(ExchangeMessage.created_at.desc())
    )
    return list(result.scalars().all())


async def list_messages_for_student(
    db: AsyncSession, student_id: str
) -> list[ExchangeMessage]:
    result = await db.execute(
        select(ExchangeMessage)
        .where(ExchangeMessage.student_id == student_id)
        .order_by(ExchangeMessage.created_at.desc())
    )
    return list(result.scalars().all())


async def get_message(
    db: AsyncSession, message_id: str
) -> Optional[ExchangeMessage]:
    result = await db.execute(
        select(ExchangeMessage).where(ExchangeMessage.id == message_id)
    )
    return result.scalar_one_or_none()


async def mark_read(db: AsyncSession, msg: ExchangeMessage) -> ExchangeMessage:
    if msg.status == "unread":
        msg.status = "read"
        msg.read_at = datetime.now(timezone.utc)
        await db.flush()
    return msg


async def apply_quick_reply(
    db: AsyncSession,
    msg: ExchangeMessage,
    quick_reply: str,
    reply_text: Optional[str],
) -> ExchangeMessage:
    msg.student_quick_reply = quick_reply
    msg.student_reply_text = reply_text
    msg.status = "replied"
    msg.replied_at = datetime.now(timezone.utc)
    await db.flush()
    return msg


async def toggle_pin(db: AsyncSession, msg: ExchangeMessage) -> ExchangeMessage:
    msg.pinned = not msg.pinned
    await db.flush()
    return msg


async def count_unread(db: AsyncSession, student_id: str) -> int:
    result = await db.execute(
        select(func.count()).where(
            ExchangeMessage.student_id == student_id,
            ExchangeMessage.status == "unread",
        )
    )
    return result.scalar_one() or 0
