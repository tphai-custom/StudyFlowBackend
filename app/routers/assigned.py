"""Router: parent-assigned tasks, habits, ideas, parent settings (Giao nhiệm vụ)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.crud import assigned as crud
from app.crud import exchange as exchange_crud
from app.crud import parent as parent_crud
from app.database import get_db
from app.models.user import User
from app.schemas.assigned import (
    AssignedHabitCreate,
    AssignedHabitSchema,
    AssignedHabitUpdate,
    AssignedHabitWithStatus,
    AssignedTaskCreate,
    AssignedTaskSchema,
    AssignedTaskUpdate,
    HabitTickCreate,
    HabitTickSchema,
    IdeaAccept,
    IdeaCreate,
    IdeaSchema,
    ParentSettingsSchema,
    ParentSettingsUpdate,
    StudentTaskAction,
    TaskItemCreate,
    TaskItemSchema,
    TaskItemUpdate,
    TaskUpdateCreate,
    TaskUpdateSchema,
)

router = APIRouter(tags=["assigned"])


# ---------------------------------------------------------------------------
# Helpers
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


# ---------------------------------------------------------------------------
# Parent – Assigned Tasks
# ---------------------------------------------------------------------------

@router.post(
    "/parent/{child_id}/assigned-tasks",
    response_model=AssignedTaskSchema,
    status_code=status.HTTP_201_CREATED,
)
async def parent_create_assigned_task(
    child_id: str,
    payload: AssignedTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, child_id)
    task = await crud.create_assigned_task(db, current_user.id, child_id, payload)
    await db.commit()
    await db.refresh(task)
    return task


@router.get(
    "/parent/{child_id}/assigned-tasks",
    response_model=list[AssignedTaskSchema],
)
async def parent_list_assigned_tasks(
    child_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, child_id)
    return await crud.list_assigned_tasks_for_parent(db, current_user.id, child_id)


@router.patch(
    "/parent/assigned-tasks/{task_id}",
    response_model=AssignedTaskSchema,
)
async def parent_update_assigned_task(
    task_id: str,
    payload: AssignedTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    task = await crud.get_assigned_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Nhiệm vụ không tồn tại")
    if task.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền sửa nhiệm vụ này")
    task = await crud.update_assigned_task(db, task, payload)
    await db.commit()
    await db.refresh(task)
    return task


# ---------------------------------------------------------------------------
# Student – Assigned Tasks
# ---------------------------------------------------------------------------

@router.get(
    "/student/assigned-tasks",
    response_model=list[AssignedTaskSchema],
)
async def student_list_assigned_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return await crud.list_assigned_tasks_for_student(db, current_user.id)


@router.post(
    "/student/assigned-tasks/{task_id}/accept",
    response_model=AssignedTaskSchema,
)
async def student_accept_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    task = await crud.get_assigned_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Nhiệm vụ không tồn tại")
    if task.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    if task.status == "ASSIGNED" or task.status == "SEEN":
        task.status = "ACCEPTED"
        await db.flush()
    await db.commit()
    await db.refresh(task)
    return task


@router.post(
    "/student/assigned-tasks/{task_id}/done",
    response_model=AssignedTaskSchema,
)
async def student_mark_task_done(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    task = await crud.get_assigned_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Nhiệm vụ không tồn tại")
    if task.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    task.status = "DONE"
    await db.flush()
    await db.commit()
    await db.refresh(task)
    return task


@router.post(
    "/student/assigned-tasks/{task_id}/request-reschedule",
    response_model=AssignedTaskSchema,
)
async def student_request_reschedule(
    task_id: str,
    payload: StudentTaskAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    task = await crud.get_assigned_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Nhiệm vụ không tồn tại")
    if task.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    task = await crud.student_update_task(
        db, task,
        student_note=payload.student_note,
        reschedule_date=payload.reschedule_requested_date,
        reschedule_reason=payload.reschedule_reason,
    )
    await db.commit()
    await db.refresh(task)
    return task


# ---------------------------------------------------------------------------
# Parent – Assigned Habits
# ---------------------------------------------------------------------------

@router.post(
    "/parent/{child_id}/assigned-habits",
    response_model=AssignedHabitSchema,
    status_code=status.HTTP_201_CREATED,
)
async def parent_create_assigned_habit(
    child_id: str,
    payload: AssignedHabitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, child_id)
    habit = await crud.create_assigned_habit(db, current_user.id, child_id, payload)
    await db.commit()
    await db.refresh(habit)
    return habit


@router.get(
    "/parent/{child_id}/assigned-habits",
    response_model=list[AssignedHabitSchema],
)
async def parent_list_assigned_habits(
    child_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, child_id)
    return await crud.list_assigned_habits_for_parent(db, current_user.id, child_id)


@router.patch(
    "/parent/assigned-habits/{habit_id}",
    response_model=AssignedHabitSchema,
)
async def parent_update_assigned_habit(
    habit_id: str,
    payload: AssignedHabitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    habit = await crud.get_assigned_habit(db, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Không tìm thấy thói quen")
    if habit.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền sửa thói quen này")
    habit = await crud.update_assigned_habit(db, habit, payload)
    await db.commit()
    await db.refresh(habit)
    return habit


@router.post(
    "/parent/assigned-habits/{habit_id}/praise",
    status_code=status.HTTP_201_CREATED,
)
async def parent_praise_habit(
    habit_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    """Send an auto praise message to the student."""
    habit = await crud.get_assigned_habit(db, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Không tìm thấy thói quen")
    if habit.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền")
    msg = await exchange_crud.create_message(
        db,
        parent_id=current_user.id,
        student_id=habit.student_id,
        content=f"🌟 Ba/Mẹ rất tự hào vì con đã duy trì thói quen '{habit.name}'. Tiếp tục phát huy nhé!",
        tag="praise",
        sender_role="parent",
    )
    await db.commit()
    await db.refresh(msg)
    return {"message_id": msg.id, "content": msg.content}


# ---------------------------------------------------------------------------
# Student – Assigned Habits
# ---------------------------------------------------------------------------

@router.get(
    "/student/assigned-habits",
    response_model=list[AssignedHabitWithStatus],
)
async def student_list_assigned_habits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    habits = await crud.list_assigned_habits_for_student(db, current_user.id)
    today_str = crud._tz_today()
    result = []
    for h in habits:
        tick = await crud.get_habit_ticked_today(db, h.id, current_user.id, today_str)
        streak, last_7 = await crud.compute_habit_streak_and_days(db, h.id, current_user.id, today_str)
        item = AssignedHabitWithStatus(
            **{c.key: getattr(h, c.key) for c in h.__table__.columns},
            ticked_today=tick is not None,
            ticked_at=tick.created_at if tick else None,
            streak=streak,
            last_7_days=last_7,
        )
        result.append(item)
    return result


@router.post(
    "/student/assigned-habits/{habit_id}/tick-today",
    response_model=AssignedHabitWithStatus,
    status_code=status.HTTP_201_CREATED,
)
async def student_tick_habit(
    habit_id: str,
    payload: HabitTickCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    habit = await crud.get_assigned_habit(db, habit_id)
    if not habit:
        raise HTTPException(status_code=404, detail="Không tìm thấy thói quen")
    if habit.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    tick = await crud.tick_habit(db, habit_id, current_user.id, payload)
    await db.commit()
    await db.refresh(tick)
    today_str = crud._tz_today()
    streak, last_7 = await crud.compute_habit_streak_and_days(db, habit_id, current_user.id, today_str)
    return AssignedHabitWithStatus(
        **{c.key: getattr(habit, c.key) for c in habit.__table__.columns},
        ticked_today=True,
        ticked_at=tick.created_at,
        streak=streak,
        last_7_days=last_7,
    )


# ---------------------------------------------------------------------------
# Ideas
# ---------------------------------------------------------------------------

@router.post(
    "/parent/{child_id}/ideas",
    response_model=IdeaSchema,
    status_code=status.HTTP_201_CREATED,
)
async def parent_create_idea(
    child_id: str,
    payload: IdeaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, child_id)
    idea = await crud.create_idea(db, current_user.id, child_id, payload)
    await db.commit()
    await db.refresh(idea)
    return idea


@router.get(
    "/student/ideas",
    response_model=list[IdeaSchema],
)
async def student_list_ideas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    return await crud.list_ideas_for_student(db, current_user.id)


@router.post(
    "/student/ideas/{idea_id}/accept",
    status_code=status.HTTP_200_OK,
)
async def student_accept_idea(
    idea_id: str,
    payload: IdeaAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    idea = await crud.get_idea(db, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề xuất")
    if idea.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    idea.status = "accepted"

    result = {"idea_id": idea.id, "status": "accepted"}

    if payload.convert_type == "task":
        from app.models.task import Task
        import uuid as _uuid
        from datetime import datetime, timezone, timedelta
        task = Task(
            id=str(_uuid.uuid4()),
            subject="Đề xuất",
            title=idea.content[:80],
            deadline=(datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
            timezone="Asia/Ho_Chi_Minh",
            difficulty=2,
            duration_estimate_min=30,
            duration_estimate_max=60,
            duration_unit="minutes",
            estimated_minutes=30,
            notes=f"[Chuyển từ đề xuất phụ huynh: {idea.id}]",
            owner_user_id=current_user.id,
            created_by_role="student",
        )
        db.add(task)
        result["task_id"] = task.id
    elif payload.convert_type == "habit":
        from app.models.habit import Habit
        import uuid as _uuid
        habit = Habit(
            id=str(_uuid.uuid4()),
            name=idea.content[:80],
            cadence="daily",
            minutes=15,
            owner_user_id=current_user.id,
        )
        db.add(habit)
        result["habit_id"] = habit.id

    await db.flush()
    await db.commit()
    return result


@router.post(
    "/student/ideas/{idea_id}/later",
    status_code=status.HTTP_200_OK,
)
async def student_defer_idea(
    idea_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    idea = await crud.get_idea(db, idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề xuất")
    if idea.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập")
    idea.status = "later"
    await db.flush()
    await db.commit()
    return {"idea_id": idea.id, "status": "later"}


# ---------------------------------------------------------------------------
# Parent Settings
# ---------------------------------------------------------------------------

@router.get(
    "/parent/settings-assign",
    response_model=ParentSettingsSchema,
)
async def get_parent_assign_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    s = await crud.get_or_create_parent_settings(db, current_user.id)
    await db.commit()
    await db.refresh(s)
    return s


@router.patch(
    "/parent/settings-assign",
    response_model=ParentSettingsSchema,
)
async def update_parent_assign_settings(
    payload: ParentSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    s = await crud.get_or_create_parent_settings(db, current_user.id)
    s = await crud.update_parent_settings(db, s, payload)
    await db.commit()
    await db.refresh(s)
    return s


# ---------------------------------------------------------------------------
# P1 – Parent: task items (checklist)
# ---------------------------------------------------------------------------

@router.post(
    "/parent/assigned-tasks/{task_id}/items",
    response_model=TaskItemSchema,
    status_code=status.HTTP_201_CREATED,
)
async def parent_add_task_item(
    task_id: str,
    payload: TaskItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    task = await crud.get_assigned_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Nhiệm vụ không tồn tại")
    if task.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền")
    item = await crud.create_task_item(db, task_id, payload)
    await db.commit()
    await db.refresh(item)
    return item


@router.get(
    "/parent/assigned-tasks/{task_id}/items",
    response_model=list[TaskItemSchema],
)
async def parent_list_task_items(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    task = await crud.get_assigned_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Nhiệm vụ không tồn tại")
    if task.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền")
    return await crud.list_task_items(db, task_id)


@router.get(
    "/student/assigned-tasks/{task_id}/items",
    response_model=list[TaskItemSchema],
)
async def student_list_task_items(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    task = await crud.get_assigned_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Nhiệm vụ không tồn tại")
    if task.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền")
    return await crud.list_task_items(db, task_id)


@router.patch(
    "/student/assigned-tasks/{task_id}/items/{item_id}",
    response_model=TaskItemSchema,
)
async def student_update_task_item(
    task_id: str,
    item_id: str,
    payload: TaskItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    task = await crud.get_assigned_task(db, task_id)
    if not task or task.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền")
    item = await crud.get_task_item(db, item_id)
    if not item or item.task_id != task_id:
        raise HTTPException(status_code=404, detail="Mục không tồn tại")
    item = await crud.update_task_item(db, item, payload, actor_role="student")
    await db.commit()
    await db.refresh(item)
    return item


# ---------------------------------------------------------------------------
# P1 – Student: quick update / activity log
# ---------------------------------------------------------------------------

@router.post(
    "/student/assigned-tasks/{task_id}/quick-update",
    response_model=TaskUpdateSchema,
    status_code=status.HTTP_201_CREATED,
)
async def student_quick_task_update(
    task_id: str,
    payload: TaskUpdateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    task = await crud.get_assigned_task(db, task_id)
    if not task or task.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền")
    upd = await crud.create_task_update(db, task_id, "student", payload)
    # Sync note on task if type is note/reschedule
    if payload.type == "request_help" or payload.type == "note":
        task.student_note = payload.content
    elif payload.type == "reschedule":
        task.reschedule_reason = payload.content
    await db.commit()
    await db.refresh(upd)
    return upd


@router.get(
    "/student/assigned-tasks/{task_id}/updates",
    response_model=list[TaskUpdateSchema],
)
async def student_list_task_updates(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    task = await crud.get_assigned_task(db, task_id)
    if not task or task.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền")
    return await crud.list_task_updates(db, task_id)


@router.get(
    "/parent/assigned-tasks/{task_id}/updates",
    response_model=list[TaskUpdateSchema],
)
async def parent_list_task_updates(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    task = await crud.get_assigned_task(db, task_id)
    if not task or task.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền")
    return await crud.list_task_updates(db, task_id)


# ---------------------------------------------------------------------------
# P2 – Parent: habit with status (streak + 7-day dots)
# ---------------------------------------------------------------------------

@router.get(
    "/parent/{child_id}/assigned-habits-status",
    response_model=list[AssignedHabitWithStatus],
)
async def parent_list_habits_with_status(
    child_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("parent")),
):
    await _require_active_link(db, current_user.id, child_id)
    habits = await crud.list_assigned_habits_for_parent(db, current_user.id, child_id)
    today_str = crud._tz_today()
    result = []
    for h in habits:
        tick = await crud.get_habit_ticked_today(db, h.id, child_id, today_str)
        streak, last_7 = await crud.compute_habit_streak_and_days(db, h.id, child_id, today_str)
        result.append(AssignedHabitWithStatus(
            **{c.key: getattr(h, c.key) for c in h.__table__.columns},
            ticked_today=tick is not None,
            ticked_at=tick.created_at if tick else None,
            streak=streak,
            last_7_days=last_7,
        ))
    return result
