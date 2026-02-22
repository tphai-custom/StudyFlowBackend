"""CRUD helpers for parent–student linking, suggestions, notes, and weekly summary."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parent import ParentStudentLink, ParentSuggestion, ParentNote
from app.models.user import User
from app.models.task import Task
from app.models.plan import PlanRecord
from app.models.free_slot import FreeSlot


class LinkedStudentInfo:
    """Simple data container for enriched link info."""
    def __init__(self, student_id: str, username: str, full_name: str, linked_at):
        self.student_id = student_id
        self.username = username
        self.full_name = full_name
        self.linked_at = linked_at


async def get_link(db: AsyncSession, parent_id: str, student_id: str) -> Optional[ParentStudentLink]:
    result = await db.execute(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == parent_id,
            ParentStudentLink.student_id == student_id,
        )
    )
    return result.scalar_one_or_none()


async def create_link(db: AsyncSession, parent_id: str, student_id: str) -> ParentStudentLink:
    link = ParentStudentLink(
        id=str(uuid.uuid4()),
        parent_id=parent_id,
        student_id=student_id,
        status="pending",
    )
    db.add(link)
    await db.flush()
    return link


async def list_links_for_parent(
    db: AsyncSession, parent_id: str, status: Optional[str] = None
) -> list[ParentStudentLink]:
    stmt = select(ParentStudentLink).where(ParentStudentLink.parent_id == parent_id)
    if status:
        stmt = stmt.where(ParentStudentLink.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_links_for_student(
    db: AsyncSession, student_id: str
) -> list[ParentStudentLink]:
    result = await db.execute(
        select(ParentStudentLink).where(ParentStudentLink.student_id == student_id)
    )
    return list(result.scalars().all())


async def get_linked_students(
    db: AsyncSession, parent_id: str
) -> list[LinkedStudentInfo]:
    """Return enriched info for all actively linked students of a parent."""
    result = await db.execute(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == parent_id,
            ParentStudentLink.status == "active",
        )
    )
    links = list(result.scalars().all())
    enriched = []
    for link in links:
        user_result = await db.execute(select(User).where(User.id == link.student_id))
        user = user_result.scalar_one_or_none()
        if user:
            enriched.append(LinkedStudentInfo(
                student_id=user.id,
                username=user.username,
                full_name=f"{user.last_name} {user.first_name}".strip(),
                linked_at=link.created_at,
            ))
    return enriched


async def update_link_status(
    db: AsyncSession, link_id: str, status: str
) -> Optional[ParentStudentLink]:
    result = await db.execute(
        select(ParentStudentLink).where(ParentStudentLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    if link:
        link.status = status
        await db.flush()
    return link


# ---- Suggestions ----

async def create_suggestion(
    db: AsyncSession,
    parent_id: str,
    student_id: str,
    type_: str,
    payload: dict,
    message: Optional[str] = None,
) -> ParentSuggestion:
    suggestion = ParentSuggestion(
        id=str(uuid.uuid4()),
        parent_id=parent_id,
        student_id=student_id,
        type=type_,
        payload=payload,
        message=message,
        status="pending",
    )
    db.add(suggestion)
    await db.flush()
    return suggestion


async def list_suggestions_for_student(
    db: AsyncSession, student_id: str, status: Optional[str] = None
) -> list[ParentSuggestion]:
    stmt = select(ParentSuggestion).where(ParentSuggestion.student_id == student_id)
    if status:
        stmt = stmt.where(ParentSuggestion.status == status)
    result = await db.execute(stmt.order_by(ParentSuggestion.created_at.desc()))
    return list(result.scalars().all())


async def list_suggestions_by_parent(
    db: AsyncSession, parent_id: str
) -> list[ParentSuggestion]:
    result = await db.execute(
        select(ParentSuggestion)
        .where(ParentSuggestion.parent_id == parent_id)
        .order_by(ParentSuggestion.created_at.desc())
    )
    return list(result.scalars().all())


async def update_suggestion_status(
    db: AsyncSession, suggestion_id: str, status: str, student_id: str
) -> Optional[ParentSuggestion]:
    result = await db.execute(
        select(ParentSuggestion).where(
            ParentSuggestion.id == suggestion_id,
            ParentSuggestion.student_id == student_id,
        )
    )
    suggestion = result.scalar_one_or_none()
    if suggestion:
        suggestion.status = status
        await db.flush()
    return suggestion


# ---------------------------------------------------------------------------
# Weekly Summary
# ---------------------------------------------------------------------------

def _week_bounds(week_str: Optional[str] = None):
    """Return (monday, sunday) datetime bounds for a given YYYY-WW or current week."""
    if week_str:
        try:
            year, wk = week_str.split("-W") if "-W" in week_str else week_str.split("-")
            monday = datetime.strptime(f"{year}-W{wk}-1", "%Y-W%W-%w").replace(tzinfo=timezone.utc)
        except Exception:
            monday = None
    else:
        monday = None
    if monday is None:
        today = datetime.now(tz=timezone.utc)
        monday = today - timedelta(days=today.weekday())
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


async def get_weekly_summary(
    db: AsyncSession,
    student_id: str,
    week_str: Optional[str] = None,
):
    """Compute weekly progress summary for a student."""
    from app.schemas.parent import WeeklySummary, UpcomingDeadline

    monday, sunday = _week_bounds(week_str)
    week_label = monday.strftime("%Y-W%W")

    # Latest plan
    plan_result = await db.execute(
        select(PlanRecord)
        .where(PlanRecord.owner_user_id == student_id)
        .order_by(PlanRecord.created_at.desc())
        .limit(1)
    )
    plan = plan_result.scalar_one_or_none()

    total_sessions = 0
    done_sessions = 0
    planned_minutes = 0
    alerts = []

    if plan and plan.sessions:
        for s in plan.sessions:
            ps = s.get("plannedStart") or s.get("planned_start", "")
            try:
                dt = datetime.fromisoformat(ps.replace("Z", "+00:00"))
                if monday <= dt <= sunday:
                    total_sessions += 1
                    planned_minutes += s.get("minutes", 0)
                    if s.get("status") == "done":
                        done_sessions += 1
            except Exception:
                pass
    else:
        alerts.append("Kế hoạch chưa được tạo")

    completion_rate = round((done_sessions / total_sessions * 100) if total_sessions else 0, 1)

    # Free slots
    slots_result = await db.execute(
        select(FreeSlot).where(FreeSlot.owner_user_id == student_id)
    )
    slots = list(slots_result.scalars().all())
    free_slot_minutes = sum(
        (s.capacity_minutes or 0) for s in slots
    ) if slots else 0

    if not slots:
        alerts.append("Tuần này chưa có slot rảnh")

    if free_slot_minutes > 0 and planned_minutes > free_slot_minutes:
        deficit = planned_minutes - free_slot_minutes
        alerts.append(f"Tuần này thiếu {deficit} phút so với kế hoạch")

    if total_sessions > 0 and completion_rate < 60:
        alerts.append(f"Điểm hoàn thành thấp ({completion_rate:.0f}%)")

    # Upcoming deadlines (tasks due within 7 days)
    now = datetime.now(tz=timezone.utc)
    tasks_result = await db.execute(
        select(Task).where(Task.owner_user_id == student_id)
    )
    tasks = list(tasks_result.scalars().all())
    upcoming = []
    for t in tasks:
        try:
            dl = t.deadline
            if isinstance(dl, str):
                dl = datetime.fromisoformat(dl.replace("Z", "+00:00"))
            if dl.tzinfo is None:
                dl = dl.replace(tzinfo=timezone.utc)
            days_left = (dl - now).days
            if 0 <= days_left <= 7 and (t.progress_minutes or 0) < (t.estimated_minutes or 1):
                upcoming.append(UpcomingDeadline(
                    task_id=t.id,
                    title=t.title,
                    subject=t.subject or "",
                    deadline=dl.isoformat(),
                    days_left=days_left,
                ))
        except Exception:
            pass
    upcoming.sort(key=lambda x: x.days_left)

    return WeeklySummary(
        student_id=student_id,
        week=week_label,
        total_minutes=sum(s.get("minutes", 0) for s in (plan.sessions or []) if _in_week(s, monday, sunday)) if plan else 0,
        completion_rate=completion_rate,
        upcoming_deadlines=upcoming[:5],
        alerts=alerts,
        total_sessions=total_sessions,
        done_sessions=done_sessions,
        free_slot_minutes=free_slot_minutes,
        planned_minutes=planned_minutes,
    )


def _in_week(session: dict, monday: datetime, sunday: datetime) -> bool:
    ps = session.get("plannedStart") or session.get("planned_start", "")
    try:
        dt = datetime.fromisoformat(ps.replace("Z", "+00:00"))
        return monday <= dt <= sunday
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Parent Notes (journal)
# ---------------------------------------------------------------------------

async def create_note(
    db: AsyncSession,
    parent_id: str,
    student_id: str,
    message: str,
    tag: str = "general",
) -> ParentNote:
    note = ParentNote(
        id=str(uuid.uuid4()),
        parent_id=parent_id,
        student_id=student_id,
        message=message,
        tag=tag,
    )
    db.add(note)
    await db.flush()
    return note


async def list_notes(
    db: AsyncSession,
    student_id: str,
    parent_id: Optional[str] = None,
) -> list[ParentNote]:
    stmt = select(ParentNote).where(ParentNote.student_id == student_id)
    if parent_id:
        stmt = stmt.where(ParentNote.parent_id == parent_id)
    result = await db.execute(stmt.order_by(ParentNote.created_at.desc()))
    return list(result.scalars().all())


async def add_note_reaction(
    db: AsyncSession,
    note_id: str,
    student_id: str,
    reaction: str,
) -> Optional[ParentNote]:
    result = await db.execute(
        select(ParentNote).where(
            ParentNote.id == note_id,
            ParentNote.student_id == student_id,
        )
    )
    note = result.scalar_one_or_none()
    if note:
        note.reaction = reaction
        await db.flush()
    return note
