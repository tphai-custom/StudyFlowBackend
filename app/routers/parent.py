"""Router: parent–student linking, child data view, suggestions, notes, weekly summary."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.crud import parent as crud
from app.crud import tasks as tasks_crud
from app.crud import plan as plan_crud
from app.crud import habits as habits_crud
from app.crud import user as user_crud
from app.database import get_db
from app.models.user import User
from app.schemas.parent import (
    LinkRequest,
    LinkSchema,
    LinkStatusUpdate,
    LinkedStudentSchema,
    NoteCreate,
    NoteReaction,
    NoteSchema,
    NudgeSettings,
    SuggestionCreate,
    SuggestionSchema,
    SuggestionStatusUpdate,
    WeeklySummary,
    DailyReport,
    SettingsLockUpdate,
    SettingsLockSchema,
)
from app.schemas.task import ParentTaskCreate, TaskSchema

router = APIRouter(prefix="/parent", tags=["parent"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _require_active_link(
    db: AsyncSession, parent_id: str, student_id: str
) -> None:
    """Raise 403 unless an active link exists between parent and student."""
    link = await crud.get_link(db, parent_id, student_id)
    if not link or link.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có liên kết hợp lệ với học sinh này.",
        )


# ---------------------------------------------------------------------------
# Link management (parent initiates)
# ---------------------------------------------------------------------------

@router.post("/link", response_model=LinkSchema, status_code=status.HTTP_201_CREATED)
async def request_link(
    payload: LinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Parent requests to link with a student using the student's link_code."""
    student = await user_crud.get_user_by_username(db, payload.child_username)
    if not student or student.role != "student":
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh")
    if student.link_code != payload.link_code:
        raise HTTPException(status_code=400, detail="Mã liên kết không đúng")
    existing = await crud.get_link(db, current_user.id, student.id)
    if existing:
        raise HTTPException(status_code=409, detail="Đã gửi yêu cầu liên kết trước đó")
    link = await crud.create_link(db, current_user.id, student.id)
    await db.commit()
    return link


@router.get("/links", response_model=list[LinkSchema])
async def list_links(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """List all links (any status) initiated by this parent."""
    return await crud.list_links_for_parent(db, current_user.id)


@router.get("/children", response_model=list[LinkSchema])
async def list_children(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """List students with active links."""
    return await crud.list_links_for_parent(db, current_user.id, status="active")


@router.get("/linked-students", response_model=list[LinkedStudentSchema])
async def linked_students(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Return enriched student info (name, username) for all linked students."""
    students = await crud.get_linked_students(db, current_user.id)
    return [
        LinkedStudentSchema(
            student_id=s.student_id,
            username=s.username,
            full_name=s.full_name,
            linked_at=s.linked_at,
        )
        for s in students
    ]


# ---------------------------------------------------------------------------
# Student responds to incoming link requests
# ---------------------------------------------------------------------------

@router.get("/incoming-links", response_model=list[LinkSchema])
async def incoming_links(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student sees who wants to link with them."""
    return await crud.list_links_for_student(db, current_user.id)


@router.patch("/links/{link_id}", response_model=LinkSchema)
async def respond_to_link(
    link_id: str,
    payload: LinkStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student accepts or rejects a link request."""
    if payload.status not in ("active", "rejected"):
        raise HTTPException(status_code=400, detail="status phải là 'active' hoặc 'rejected'")
    link = await crud.update_link_status(db, link_id, payload.status)
    if not link or link.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu liên kết")
    await db.commit()
    return link


# ---------------------------------------------------------------------------
# Parent reads child data
# ---------------------------------------------------------------------------

@router.get("/child/{student_id}/tasks")
async def get_child_tasks(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    return await tasks_crud.list_tasks(db, student_id)


@router.get("/child/{student_id}/plan")
async def get_child_plan(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    plan = await plan_crud.get_latest_plan(db, student_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Chưa có kế hoạch")
    return plan


@router.get("/child/{student_id}/habits")
async def get_child_habits(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    return await habits_crud.list_habits(db, student_id)


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------

@router.post("/child/{student_id}/suggestions", response_model=SuggestionSchema, status_code=status.HTTP_201_CREATED)
async def create_suggestion(
    student_id: str,
    payload: SuggestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    suggestion = await crud.create_suggestion(
        db,
        parent_id=current_user.id,
        student_id=student_id,
        type_=payload.type,
        payload=payload.payload,
        message=payload.message,
    )
    await db.commit()
    return suggestion


@router.get("/child/{student_id}/suggestions", response_model=list[SuggestionSchema])
async def list_suggestions_for_child(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    return await crud.list_suggestions_by_parent(db, current_user.id)


@router.get("/my-suggestions", response_model=list[SuggestionSchema])
async def my_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student sees suggestions sent to them (pending ones)."""
    return await crud.list_suggestions_for_student(db, current_user.id, status="pending")


@router.patch("/suggestions/{suggestion_id}", response_model=SuggestionSchema)
async def respond_to_suggestion(
    suggestion_id: str,
    payload: SuggestionStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    if payload.status not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="status phải là 'accepted' hoặc 'rejected'")
    suggestion = await crud.update_suggestion_status(
        db, suggestion_id, payload.status, current_user.id
    )
    if not suggestion:
        raise HTTPException(status_code=404, detail="Không tìm thấy gợi ý")
    await db.commit()
    return suggestion


# ---------------------------------------------------------------------------
# Weekly summary
# ---------------------------------------------------------------------------

@router.get("/students/{student_id}/weekly-summary", response_model=WeeklySummary)
async def child_weekly_summary(
    student_id: str,
    week: Optional[str] = Query(default=None, description="YYYY-WW, e.g. 2026-W08"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Return weekly progress summary for a linked student."""
    await _require_active_link(db, current_user.id, student_id)
    return await crud.get_weekly_summary(db, student_id, week)


@router.get("/students/{student_id}/daily-report", response_model=DailyReport)
async def child_daily_report(
    student_id: str,
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD; defaults to today"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Return daily planned vs done minutes for a linked student."""
    await _require_active_link(db, current_user.id, student_id)
    return await crud.get_daily_report(db, student_id, date)


# ---------------------------------------------------------------------------
# Parent Settings Lock
# ---------------------------------------------------------------------------

@router.get("/students/{student_id}/settings-lock", response_model=SettingsLockSchema)
async def get_student_settings_lock(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Get locked settings fields for a linked student (returns empty lock if none set)."""
    await _require_active_link(db, current_user.id, student_id)
    lock = await crud.get_settings_lock(db, student_id, current_user.id)
    if lock is None:
        return SettingsLockSchema(student_id=student_id, parent_id=current_user.id, locked_fields=[])
    return lock


@router.put("/students/{student_id}/settings-lock", response_model=SettingsLockSchema)
async def update_student_settings_lock(
    student_id: str,
    payload: SettingsLockUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Set which settings fields are locked for a linked student."""
    await _require_active_link(db, current_user.id, student_id)
    from app.schemas.parent import LOCKABLE_FIELDS
    # Validate: only allow known lockable fields
    invalid = [f for f in payload.locked_fields if f not in LOCKABLE_FIELDS]
    if invalid:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Không hợp lệ: {invalid}. Cho phép: {LOCKABLE_FIELDS}")
    lock = await crud.upsert_settings_lock(db, student_id, current_user.id, payload.locked_fields, payload.locked_values)
    await db.commit()
    return lock


@router.get("/student/settings-locked-fields", response_model=list[str])
async def my_locked_fields(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student endpoint: returns list of fields locked by any parent."""
    return await crud.get_locked_fields_for_student(db, current_user.id)


# ---------------------------------------------------------------------------
# Enriched child data (tasks/plan/stats with filter)
# ---------------------------------------------------------------------------

@router.get("/students/{student_id}/tasks")
async def get_student_tasks(
    student_id: str,
    filter: Optional[str] = Query(default=None, description="deadline|important|incomplete"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Return tasks for a linked student, with optional filter."""
    await _require_active_link(db, current_user.id, student_id)
    tasks = await tasks_crud.list_tasks(db, student_id)
    from datetime import datetime, timezone
    now = datetime.now(tz=timezone.utc)
    if filter == "deadline":
        tasks = sorted(tasks, key=lambda t: t.deadline)
    elif filter == "important":
        tasks = [t for t in tasks if (t.importance or 0) >= 2]
    elif filter == "incomplete":
        tasks = [t for t in tasks if (t.progress_minutes or 0) < (t.estimated_minutes or 1)]
    return tasks


@router.get("/students/{student_id}/plan")
async def get_student_plan(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Return latest plan for a linked student."""
    await _require_active_link(db, current_user.id, student_id)
    plan = await plan_crud.get_latest_plan(db, student_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Chưa có kế hoạch")
    return plan


@router.get("/students/{student_id}/stats")
async def get_student_stats(
    student_id: str,
    range: Optional[str] = Query(default="week", description="week|month"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Return learning stats for a linked student."""
    await _require_active_link(db, current_user.id, student_id)
    from datetime import datetime, timedelta, timezone
    from app.models.plan import PlanRecord
    from sqlalchemy import select

    now = datetime.now(tz=timezone.utc)
    if range == "month":
        since = now - timedelta(days=30)
    else:
        since = now - timedelta(days=7)

    plan_result = await db.execute(
        select(PlanRecord)
        .where(PlanRecord.owner_user_id == student_id)
        .order_by(PlanRecord.created_at.desc())
        .limit(1)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        return {"total_minutes": 0, "completion_rate": 0, "top_subject": None, "sessions_done": 0}

    sessions = plan.sessions or []
    total = 0
    done = 0
    subject_minutes: dict = {}
    for s in sessions:
        # E: Exclude break sessions from progress statistics
        if s.get("source") == "break":
            continue
        ps = s.get("plannedStart") or s.get("planned_start", "")
        try:
            dt = datetime.fromisoformat(ps.replace("Z", "+00:00"))
            if dt >= since:
                mins = s.get("minutes", 0)
                total += mins
                if s.get("status") == "done":
                    done += mins
                    subj = s.get("subject", "")
                    subject_minutes[subj] = subject_minutes.get(subj, 0) + mins
        except Exception:
            pass

    top_subject = max(subject_minutes, key=lambda k: subject_minutes[k]) if subject_minutes else None
    completion_rate = round((done / total * 100) if total else 0, 1)

    return {
        "total_minutes": total,
        "completion_rate": completion_rate,
        "top_subject": top_subject,
        "sessions_done": done,
        "range": range,
    }


# ---------------------------------------------------------------------------
# Nudge messages (smart suggestions)
# ---------------------------------------------------------------------------

@router.get("/students/{student_id}/nudges")
async def get_nudges(
    student_id: str,
    tone: str = Query(default="medium", description="light|medium|strict"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Return contextual nudge message templates based on current student state."""
    await _require_active_link(db, current_user.id, student_id)
    summary = await crud.get_weekly_summary(db, student_id)

    from app.models.user import User as UserModel
    from sqlalchemy import select
    student_result = await db.execute(select(UserModel).where(UserModel.id == student_id))
    student = student_result.scalar_one_or_none()
    name = student.first_name if student else "con"

    messages = []

    # Behind schedule
    if summary.completion_rate < 50 and summary.total_sessions > 0:
        if tone == "light":
            messages.append({"situation": "behind", "text": f"{name} ơi, tuần này mình cố gắng thêm một chút nhé 💪"})
        elif tone == "medium":
            messages.append({"situation": "behind", "text": f"{name} ơi, tiến độ tuần này mới được {summary.completion_rate:.0f}%. Tối nay mình làm thêm 1 phiên 45' nha?"})
        else:
            messages.append({"situation": "behind", "text": f"{name}, hoàn thành {summary.completion_rate:.0f}% là chưa đủ. Cần bắt kịp ngay hôm nay!"})

    # Upcoming deadline
    if summary.upcoming_deadlines:
        d = summary.upcoming_deadlines[0]
        if d.days_left <= 2:
            messages.append({"situation": "deadline", "text": f"Deadline {d.subject} còn {d.days_left} ngày, {name} muốn mình giúp chia nhỏ không?"})
        else:
            messages.append({"situation": "deadline", "text": f"{name} nhớ ôn {d.subject} nha, còn {d.days_left} ngày là đến deadline rồi đó."})

    # No plan
    if "Kế hoạch chưa được tạo" in summary.alerts:
        messages.append({"situation": "no_plan", "text": f"{name} ơi, mình vào StudyFlow tạo kế hoạch tuần này chưa? Ba/mẹ chờ xem nha 😊"})

    # No slots
    if "Tuần này chưa có slot rảnh" in summary.alerts:
        messages.append({"situation": "no_slots", "text": f"{name} nhớ cập nhật thời gian rảnh trong StudyFlow để hệ thống sắp lịch giúp nha."})

    # Doing well
    if summary.completion_rate >= 80:
        messages.append({"situation": "praise", "text": f"Tuần này {name} làm tốt lắm ({summary.completion_rate:.0f}%)! Mình giữ streak nhé! 🌟"})

    # Default
    if not messages:
        messages.append({"situation": "general", "text": f"{name} ơi, có cần ba/mẹ giúp gì không? Học tốt nhá!"})

    return {"student_name": name, "tone": tone, "messages": messages, "summary": summary}


# ---------------------------------------------------------------------------
# Parent Notes (journal) — P1
# ---------------------------------------------------------------------------

@router.post("/students/{student_id}/notes", response_model=NoteSchema, status_code=status.HTTP_201_CREATED)
async def create_note(
    student_id: str,
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    note = await crud.create_note(db, current_user.id, student_id, payload.message, payload.tag or "general")
    await db.commit()
    return note


@router.get("/students/{student_id}/notes", response_model=list[NoteSchema])
async def list_notes(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, student_id)
    return await crud.list_notes(db, student_id, parent_id=current_user.id)


@router.post("/notes/{note_id}/reaction", response_model=NoteSchema)
async def react_to_note(
    note_id: str,
    payload: NoteReaction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student reacts to a parent note."""
    note = await crud.add_note_reaction(db, note_id, current_user.id, payload.reaction)
    if not note:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi chú")
    await db.commit()
    return note


@router.get("/student/notes", response_model=list[NoteSchema])
async def student_notes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    """Student sees all notes sent to them."""
    return await crud.list_notes(db, current_user.id)


# ---------------------------------------------------------------------------
# Parent creates a task for a linked student (B/H)
# ---------------------------------------------------------------------------

@router.post("/tasks", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def parent_create_task(
    payload: ParentTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Parent assigns a task directly into the student's task list."""
    await _require_active_link(db, current_user.id, payload.student_id)
    task = await tasks_crud.create_parent_task(
        db,
        parent_id=current_user.id,
        student_id=payload.student_id,
        title=payload.title,
        subject=payload.subject,
        description=payload.description,
        deadline=payload.deadline,
        estimated_minutes=payload.estimated_minutes,
        priority=payload.priority,
        locked=payload.locked,
        repeat=payload.repeat,
    )
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/students/{student_id}/tasks", response_model=list[TaskSchema])
async def parent_list_student_tasks(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Parent views all tasks belonging to a linked student."""
    await _require_active_link(db, current_user.id, student_id)
    return await tasks_crud.list_tasks(db, student_id)
