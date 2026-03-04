"""Router: exchange messages between parent and student (Trao đổi)."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.crud import exchange as crud
from app.crud import parent as parent_crud
from app.crud import tasks as tasks_crud
from app.database import get_db
from app.models.user import User
from app.schemas.exchange import (
    BadgeCountSchema,
    BannerItem,
    ExchangeBadgeSummary,
    ExchangeMessageCreate,
    ExchangeMessageSchema,
    ExchangeSummary,
    MessageActionAddChecklist,
    MessageActionCreateSession,
    MessageActionCreateTask,
    ProgressSummary,
    QuickReplyCreate,
    TodayHabitSummary,
    UnreadCountSchema,
)

router = APIRouter(tags=["exchange"])


# ---------------------------------------------------------------------------
# Badge summary (unified source of truth for sidebar + dashboard)
# ---------------------------------------------------------------------------

@router.get(
    "/exchange/badge-summary",
    response_model=ExchangeBadgeSummary,
)
async def student_badge_summary(
    today: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Unified badge count for sidebar + dashboard. Single source of truth."""
    from datetime import date
    today_date = today or date.today().isoformat()
    result = await crud.exchange_summary(db, current_user.id, today_date)
    pending_habits = max(
        0,
        result["today_parent_habits"]["total"] - result["today_parent_habits"]["done"],
    )
    unread = result["unread_parent_messages"]
    need_reply = result.get("need_reply_messages", unread)
    pending_tasks = result["open_parent_tasks"]
    # exchange_badge_total = unread + pending_tasks(ASSIGNED|SEEN) + pending_habits_today
    total = unread + pending_tasks + pending_habits
    return ExchangeBadgeSummary(
        unread_messages=unread,
        need_reply_messages=need_reply,
        pending_parent_tasks=pending_tasks,
        pending_parent_habits_today=pending_habits,
        # legacy aliases
        pending_tasks=pending_tasks,
        pending_habits=pending_habits,
        total_badge=total,
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _require_active_link(
    db: AsyncSession, parent_id: str, student_id: str
) -> None:
    link = await parent_crud.get_link(db, parent_id, student_id)
    if not link or link.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có liên kết hợp lệ với học sinh này.",
        )


async def _get_msg_owned_by_student(
    db: AsyncSession, message_id: str, student_id: str
):
    msg = await crud.get_message(db, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Tin nhắn không tồn tại")
    if msg.student_id != student_id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập tin nhắn này")
    return msg


# ---------------------------------------------------------------------------
# Parent endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/parent/{child_id}/messages",
    response_model=ExchangeMessageSchema,
    status_code=status.HTTP_201_CREATED,
)
async def parent_send_message(
    child_id: str,
    payload: ExchangeMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Parent sends a message to a linked student."""
    await _require_active_link(db, current_user.id, child_id)
    msg = await crud.create_message(
        db,
        parent_id=current_user.id,
        student_id=child_id,
        content=payload.content,
        tag=payload.tag,
        sender_role="parent",
    )
    await db.commit()
    await db.refresh(msg)
    return msg


@router.get(
    "/parent/{child_id}/messages",
    response_model=list[ExchangeMessageSchema],
)
async def parent_list_messages(
    child_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Parent views all messages in the thread with a specific linked student."""
    await _require_active_link(db, current_user.id, child_id)
    return await crud.list_messages_for_parent(db, current_user.id, child_id)


# ---------------------------------------------------------------------------
# Student endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/student/messages",
    response_model=list[ExchangeMessageSchema],
)
async def student_list_messages(
    filter: Optional[str] = Query(default="all", description="all|unread|needs_action|done"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student views their inbox with optional filter."""
    msgs = await crud.list_messages_for_student(db, current_user.id)
    if filter == "unread":
        return [m for m in msgs if m.status == "unread"]
    elif filter == "needs_action":
        return [m for m in msgs if m.status == "read"]
    elif filter == "done":
        return [m for m in msgs if m.status == "replied"]
    return msgs


@router.get(
    "/student/messages/unread-count",
    response_model=UnreadCountSchema,
)
async def student_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Returns unread message count for badge display (only UNREAD counts)."""
    count = await crud.count_unread(db, current_user.id)
    return {"unread_count": count}


@router.get(
    "/student/messages/{message_id}",
    response_model=ExchangeMessageSchema,
)
async def student_get_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student views message detail; automatically marks as read."""
    msg = await _get_msg_owned_by_student(db, message_id, current_user.id)
    msg = await crud.mark_read(db, msg)
    await db.commit()
    await db.refresh(msg)
    return msg


@router.post(
    "/student/messages/{message_id}/mark-read",
    response_model=ExchangeMessageSchema,
)
async def student_mark_read(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    msg = await _get_msg_owned_by_student(db, message_id, current_user.id)
    msg = await crud.mark_read(db, msg)
    await db.commit()
    await db.refresh(msg)
    return msg


@router.post(
    "/student/messages/{message_id}/reply",
    response_model=ExchangeMessageSchema,
)
async def student_reply(
    message_id: str,
    payload: QuickReplyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student sends a quick reply (+ optional free text)."""
    allowed = {"LIKE", "DO_TODAY", "RESCHEDULE", "NEED_HELP"}
    if payload.quick_reply not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"quick_reply phải là một trong: {', '.join(allowed)}",
        )
    msg = await _get_msg_owned_by_student(db, message_id, current_user.id)
    msg = await crud.apply_quick_reply(db, msg, payload.quick_reply, payload.reply_text)
    await db.commit()
    await db.refresh(msg)
    return msg


@router.post(
    "/student/messages/{message_id}/pin",
    response_model=ExchangeMessageSchema,
)
async def student_pin_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Toggle pin on a message."""
    msg = await _get_msg_owned_by_student(db, message_id, current_user.id)
    msg = await crud.toggle_pin(db, msg)
    await db.commit()
    await db.refresh(msg)
    return msg


# ---------------------------------------------------------------------------
# Convert message → actions (P0)
# ---------------------------------------------------------------------------

@router.post(
    "/student/messages/{message_id}/actions/create-task",
    status_code=status.HTTP_201_CREATED,
)
async def action_create_task(
    message_id: str,
    payload: MessageActionCreateTask,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Create a Task from a message (prefilled from message content)."""
    msg = await _get_msg_owned_by_student(db, message_id, current_user.id)

    title = payload.title or msg.content[:80]
    subject = payload.subject or "Chưa phân loại"

    from app.models.task import Task
    from datetime import datetime, timedelta, timezone
    task = Task(
        id=str(uuid.uuid4()),
        subject=subject,
        title=title,
        deadline=(datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
        timezone="Asia/Ho_Chi_Minh",
        difficulty=2,
        duration_estimate_min=30,
        duration_estimate_max=60,
        duration_unit="minutes",
        estimated_minutes=30,
        notes=f"[Tạo từ tin nhắn phụ huynh: {msg.id}] {msg.content[:200]}",
        owner_user_id=current_user.id,
        created_by_role="student",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return {"task_id": task.id, "title": task.title}


@router.post(
    "/student/messages/{message_id}/actions/add-checklist-item",
    status_code=status.HTTP_200_OK,
)
async def action_add_checklist_item(
    message_id: str,
    payload: MessageActionAddChecklist,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Add a checklist item to an existing task."""
    msg = await _get_msg_owned_by_student(db, message_id, current_user.id)

    from app.models.task import Task
    from sqlalchemy import select
    result = await db.execute(
        select(Task).where(Task.id == payload.task_id, Task.owner_user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task không tồn tại hoặc không thuộc về bạn")

    criteria = list(task.success_criteria or [])
    criteria.append({"text": payload.item, "done": False, "from_message": msg.id})
    task.success_criteria = criteria
    await db.commit()
    return {"task_id": task.id, "added_item": payload.item}


@router.post(
    "/student/messages/{message_id}/actions/create-session",
    status_code=status.HTTP_201_CREATED,
)
async def action_create_session(
    message_id: str,
    payload: MessageActionCreateSession,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Create a quick task (with today's deadline) as a study session block."""
    msg = await _get_msg_owned_by_student(db, message_id, current_user.id)

    minutes = payload.minutes if payload.minutes in (25, 45) else 25

    from app.models.task import Task
    from datetime import datetime, timezone, timedelta
    today_deadline = (datetime.now(timezone.utc)).strftime("%Y-%m-%dT23:59:59")
    task = Task(
        id=str(uuid.uuid4()),
        subject="Từ tin nhắn",
        title=f"[{minutes}p] {msg.content[:60]}",
        deadline=today_deadline,
        timezone="Asia/Ho_Chi_Minh",
        difficulty=1,
        duration_estimate_min=minutes,
        duration_estimate_max=minutes,
        duration_unit="minutes",
        estimated_minutes=minutes,
        notes=f"[Phiên học tạo từ tin nhắn phụ huynh: {msg.id}]",
        owner_user_id=current_user.id,
        created_by_role="student",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return {"task_id": task.id, "minutes": minutes, "title": task.title}


@router.post(
    "/student/messages/{message_id}/actions/pin-today",
    status_code=status.HTTP_200_OK,
)
async def action_pin_today(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Pin the message so it shows in the student's Today view."""
    msg = await _get_msg_owned_by_student(db, message_id, current_user.id)
    if not msg.pinned:
        msg = await crud.toggle_pin(db, msg)
        await db.commit()
        await db.refresh(msg)
    return {"pinned": msg.pinned, "message_id": msg.id}


# ---------------------------------------------------------------------------
# Dashboard summary endpoints (P0)
# ---------------------------------------------------------------------------

@router.get(
    "/student/dashboard/exchange-summary",
    response_model=ExchangeSummary,
)
async def student_exchange_summary(
    today: Optional[str] = Query(default=None, description="YYYY-MM-DD in student timezone"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Return exchange summary counts for dashboard widget."""
    from datetime import date
    today_date = today or date.today().isoformat()
    result = await crud.exchange_summary(db, current_user.id, today_date)
    return ExchangeSummary(
        unread_parent_messages=result["unread_parent_messages"],
        open_parent_tasks=result["open_parent_tasks"],
        today_parent_habits=TodayHabitSummary(**result["today_parent_habits"]),
    )


@router.get(
    "/student/dashboard/progress-summary",
    response_model=ProgressSummary,
)
async def student_progress_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Return today vs. week progress breakdown (sessions + minutes done/planned)."""
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    result = await crud.progress_summary(db, current_user.id, now_iso)
    return ProgressSummary(
        today=result["today"],
        week=result["week"],
    )


@router.get(
    "/student/banners",
    response_model=list[BannerItem],
)
async def student_banners(
    today: Optional[str] = Query(default=None, description="YYYY-MM-DD in student timezone"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Return list of in-app banners for dashboard/today header."""
    from datetime import date
    today_date = today or date.today().isoformat()
    banners = await crud.build_banners(db, current_user.id, today_date)
    return [BannerItem(**b) for b in banners]


@router.get(
    "/parent/students/{student_id}/progress-summary",
    response_model=ProgressSummary,
)
async def parent_student_progress_summary(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Return today vs. week progress for a linked student (parent view)."""
    await _require_active_link(db, current_user.id, student_id)
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    result = await crud.progress_summary(db, student_id, now_iso)
    return ProgressSummary(
        today=result["today"],
        week=result["week"],
    )
