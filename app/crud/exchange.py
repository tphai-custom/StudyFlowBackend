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


async def exchange_summary(db: AsyncSession, student_id: str, today_date: str) -> dict:
    """Compute dashboard exchange summary: unread messages + open tasks + today habits."""
    from app.models.assigned import ParentAssignedTask, ParentAssignedHabit, HabitTick

    # Unread messages (status == 'unread')
    unread_count = await count_unread(db, student_id)

    # Messages needing reply (status == 'unread' and not system-generated — same as unread
    # but we expose as separate field for clarity; currently unread already covers it)
    # "need_reply" = messages still unread (student hasn't responded at all)
    need_reply_result = await db.execute(
        select(func.count()).where(
            ExchangeMessage.student_id == student_id,
            ExchangeMessage.status == "unread",
        )
    )
    need_reply_count = need_reply_result.scalar_one() or 0

    # Pending parent tasks = ASSIGNED or SEEN (not yet accepted/in-progress/done)
    tasks_result = await db.execute(
        select(func.count()).where(
            ParentAssignedTask.student_id == student_id,
            ParentAssignedTask.status.in_(["ASSIGNED", "SEEN"]),
        )
    )
    pending_tasks = tasks_result.scalar_one() or 0

    # Today assigned habits
    habits_result = await db.execute(
        select(ParentAssignedHabit).where(
            ParentAssignedHabit.student_id == student_id,
            ParentAssignedHabit.status == "active",
        )
    )
    active_habits = list(habits_result.scalars().all())

    # Ticks for today
    ticks_result = await db.execute(
        select(HabitTick).where(
            HabitTick.student_id == student_id,
            HabitTick.date == today_date,
            HabitTick.completed == True,
        )
    )
    ticked_habit_ids = {t.habit_id for t in ticks_result.scalars().all()}

    today_habit_ids = [h.id for h in active_habits]
    done_count = sum(1 for hid in today_habit_ids if hid in ticked_habit_ids)
    undone_ids = [hid for hid in today_habit_ids if hid not in ticked_habit_ids]

    return {
        "unread_parent_messages": unread_count,
        "need_reply_messages": need_reply_count,
        "open_parent_tasks": pending_tasks,  # only ASSIGNED|SEEN tasks
        "today_parent_habits": {
            "total": len(today_habit_ids),
            "done": done_count,
            "undone_ids": undone_ids,
        },
    }


async def progress_summary(db: AsyncSession, student_id: str, today_iso: str, tz_offset_hours: int = 7) -> dict:
    """Compute today vs. week progress from the latest plan."""
    from datetime import timedelta, timezone
    from app.models.plan import PlanRecord
    from sqlalchemy import select as sa_select

    tz = timezone(timedelta(hours=tz_offset_hours))
    now_aware = datetime.fromisoformat(today_iso)
    if now_aware.tzinfo is None:
        now_aware = now_aware.replace(tzinfo=tz)
    today_date = now_aware.astimezone(tz).date()
    week_start = today_date - timedelta(days=today_date.weekday())  # Monday

    plan_result = await db.execute(
        sa_select(PlanRecord)
        .where(PlanRecord.owner_user_id == student_id)
        .order_by(PlanRecord.created_at.desc())
        .limit(1)
    )
    plan = plan_result.scalar_one_or_none()

    empty_block = {"done_sessions": 0, "planned_sessions": 0, "done_minutes": 0, "planned_minutes": 0}
    if not plan:
        return {"today": empty_block, "week": empty_block}

    today_block = {"done_sessions": 0, "planned_sessions": 0, "done_minutes": 0, "planned_minutes": 0}
    week_block = {"done_sessions": 0, "planned_sessions": 0, "done_minutes": 0, "planned_minutes": 0}

    for s in (plan.sessions or []):
        if s.get("source") == "break":
            continue
        try:
            ps = s.get("plannedStart") or s.get("planned_start", "")
            dt = datetime.fromisoformat(ps.replace("Z", "+00:00"))
            dt_local = dt.astimezone(tz).date()
        except Exception:
            continue

        mins = s.get("minutes", 0)
        is_done = s.get("status") == "done"

        # Week
        if week_start <= dt_local <= today_date:
            week_block["planned_sessions"] += 1
            week_block["planned_minutes"] += mins
            if is_done:
                week_block["done_sessions"] += 1
                week_block["done_minutes"] += mins

        # Today
        if dt_local == today_date:
            today_block["planned_sessions"] += 1
            today_block["planned_minutes"] += mins
            if is_done:
                today_block["done_sessions"] += 1
                today_block["done_minutes"] += mins

    return {"today": today_block, "week": week_block}


async def build_banners(db: AsyncSession, student_id: str, today_date: str) -> list[dict]:
    """Build in-app banners for the student's dashboard."""
    from app.models.assigned import ParentAssignedTask, ParentAssignedHabit, HabitTick
    banners = []

    # Locked tasks not yet accepted / not in plan
    locked_result = await db.execute(
        select(ParentAssignedTask).where(
            ParentAssignedTask.student_id == student_id,
            ParentAssignedTask.locked == True,
            ParentAssignedTask.status.notin_(["DONE", "VERIFIED", "ARCHIVED"]),
        )
    )
    locked_tasks = list(locked_result.scalars().all())
    unaccepted_locked = [t for t in locked_tasks if t.status == "ASSIGNED"]
    if unaccepted_locked:
        banners.append({
            "key": "locked_task_unaccepted",
            "level": "error",
            "message": f"Ban co {len(unaccepted_locked)} nhiem vu bat buoc tu phu huynh can xac nhan",
            "href": "/exchange/assigned-tasks",
        })
    elif locked_tasks:
        banners.append({
            "key": "locked_task_accepted",
            "level": "warning",
            "message": f"Ban co {len(locked_tasks)} nhiem vu bat buoc tu phu huynh can len lich",
            "href": "/exchange/assigned-tasks",
        })

    # Unread messages
    unread = await count_unread(db, student_id)
    if unread > 0:
        banners.append({
            "key": "unread_messages",
            "level": "info",
            "message": f"Ban co {unread} tin nhan chua doc tu phu huynh",
            "href": "/exchange",
        })

    # Today habits undone
    habits_result = await db.execute(
        select(ParentAssignedHabit).where(
            ParentAssignedHabit.student_id == student_id,
            ParentAssignedHabit.status == "active",
        )
    )
    active_habits = list(habits_result.scalars().all())
    if active_habits:
        ticks_result = await db.execute(
            select(HabitTick).where(
                HabitTick.student_id == student_id,
                HabitTick.date == today_date,
                HabitTick.completed == True,
            )
        )
        ticked_ids = {t.habit_id for t in ticks_result.scalars().all()}
        undone = [h for h in active_habits if h.id not in ticked_ids]
        if undone:
            banners.append({
                "key": "habits_undone",
                "level": "warning",
                "message": f"Con {len(undone)} thoi quen hom nay chua tick",
                "href": "/exchange/assigned-habits",
            })

    return banners
